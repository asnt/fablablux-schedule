from __future__ import print_function

import sys

import cv2
import numpy as np


debug = False


def make_detector_matcher(detector_name, n_features):
    """Construct the detector and matcher objects.
    
    Parameters
    ----------
    detector_name :
        Detector name (SURF, SIFT, ORB).
    n_features :
        Number of feature points to detect. Does not apply to SURF.

    Returns
    -------
    detector :
        The detector object.
    matcher :
        The matcher object.
    """
    if detector_name == 'orb':
        detector = cv2.ORB(nfeatures=n_features)
        matcher = cv2.BFMatcher(normType=cv2.NORM_HAMMING, crossCheck=True)
    elif detector_name == 'sift':
        detector = cv2.SIFT(nfeatures=n_features)
        matcher = cv2.BFMatcher(crossCheck=True)
    elif detector_name == 'surf':
        detector = cv2.SURF(hessianThreshold=300, upright=True)
        #detector = cv2.SURF()
        matcher = cv2.BFMatcher(crossCheck=True)
    else:
        raise ValueError('unknown detector: {:s}'.format(detector) +
                         '(should be one of "orb", "sift", "surf"')

    if debug:
        print('detector = ' + detector_name)
        if detector_name != 'surf':
            print('n_features = ' + str(n_features))

    return detector, matcher


def unwarp(image, template, detector_name='surf', n_features=5000):
    """Transform an image to fit the template.

    Parameters
    ----------
    image : (M, N)
        Image to rectify.
    template : (P, Q)
        Template image.
    detector_name : string, optional
        The feature detector to be used.
    n_features : int, optional
        The number of features to use.

    Returns
    -------
    unwarped : (M', N')
        The unwarped image.
    """
    detector, matcher = make_detector_matcher(detector_name, n_features)

    keypoints1, descriptors1 = detector.detectAndCompute(template, None)
    keypoints2, descriptors2 = detector.detectAndCompute(image, None)

    matches = matcher.match(descriptors1, descriptors2)

    # Get the keypoints as Nx2 arrays from the list of OpenCV keypoints.
    keypoints1 = [keypoints1[int(m.queryIdx)].pt for m in matches]
    keypoints1 = np.array(keypoints1, dtype=np.float32)
    keypoints2 = [keypoints2[int(m.trainIdx)].pt for m in matches]
    keypoints2 = np.array(keypoints2, dtype=np.float32)

    #method = cv2.RANSAC
    method = cv2.LMEDS
    inlier_threshold = 7    # Only effective with RANSAC.
    transform_matrix, mask = cv2.findHomography(keypoints1, keypoints2,
                                                method, inlier_threshold)

    unwarped = cv2.warpPerspective(image, transform_matrix, template.T.shape,
                                   None, cv2.WARP_INVERSE_MAP)

    return unwarped


n_machines = 7
n_slots = 9

# radius of a square slot 
slot_radius = 15

# Position of the top-left slot of the table
r0, c0 = 140, 115
# Distance between successive rows (vertical direction)
d_rows = np.array([0, 62.5, 125, 220, 285, 375, 465])
d_rows = d_rows / 2 # using half resolution image
# Distance between successive cols (horizontal direction)
d_cols = 78 * np.arange(n_slots)
d_cols = d_cols / 2 # using half resolution image
# Absolution position of the slots
row_tile = np.tile(d_rows[:, np.newaxis], (1, n_slots))
col_tile = np.tile(d_cols, (n_machines, 1))
slot_position = np.dstack((r0 + row_tile, c0 + col_tile))


def find_booked_slots(image):
    """Find which slots are booked in the schedule.

    Parameters
    ----------
    image : (M, N)
        Aligned image of the schedule table.

    Returns
    -------
    schedule : (N_MACHINES, N_SLOTS), bool
        Schedule matrix (True if slot scheduled).
    """
    image_float = image.astype(float)

    roughness_threshold = 2.5   # threshold at mean intensity level == 150
    # Adapt the threshold to the image mean intensity level.
    mean_intensity = image_float.mean()
    roughness_threshold = roughness_threshold * (mean_intensity / 150)

    if debug:
        print("roughness threshold = {:.2f}".format(roughness_threshold))
    
    # Measure the slot roughness from which we deduce if a card is present.
    def roughness(patch):
        grad = np.gradient(patch)
        return np.mean(np.sqrt(grad[0]**2 + grad[1]**2))

    def is_booked(patch):
        # A slot is booked if the card is absent, i.e. the roughness is low.
        return roughness(patch) < roughness_threshold

    if debug:
        slot_roughness = np.zeros((n_machines, n_slots))

    schedule = np.zeros((n_machines, n_slots), dtype=bool)
    for machine_index in range(n_machines):
        for slot_index in range(n_slots):
            r, c = slot_position[machine_index, slot_index]
            rmin = r - slot_radius
            rmax = r + slot_radius
            cmin = c - slot_radius
            cmax = c + slot_radius
            patch = image_float[rmin:rmax, cmin:cmax]
            if is_booked(patch):
                schedule[machine_index, slot_index] = True
            if debug:
                slot_roughness[machine_index, slot_index] = roughness(patch)

    if debug:
        np.set_printoptions(precision=2)
        print(slot_roughness)

    return schedule


def highlight_slots(image):
    """Highlight the slots on the image for visualisation purpose.

    Parameters
    ----------
    image : (M, N)
        Image of the schedule.

    Returns
    -------
    highlighted : (M, N)
        Image with highlighted slots.
    """
    radius = 15

    slot_mask = np.ones_like(image, dtype=bool)
    for m in range(n_machines):
        for s in range(n_slots):
            r, c = slot_position[m, s]
            rmin = r - slot_radius
            rmax = r + slot_radius
            cmin = c - slot_radius
            cmax = c + slot_radius
            slot_mask[rmin:rmax, cmin:cmax] = False

    highlighted = image.copy()
    highlighted[slot_mask] = 0.5 * highlighted[slot_mask]

    return highlighted


def scan(image, template, detector_name=None, n_features=None):
    """Scan the schedule from the warped image.

    Parameters
    ----------
    image : (M, N, 3)
        Warped image of the schedule table.
    template : (M, N, 3)
        Non-warped template image of the schedule table.
    detector_name: string, optional
        The name of the feature detector to use.
    n_features: string, optional
        The number of features for the detector. This has no effect with the
        SURF detector.

    Returns
    -------
    schedule : (N_MACHINES, N_SLOTS), bool
        Boolean matrix indicating the booking status of the machines.
    unwarped : (M, N)
        Unwarped image.
    """
    kwargs = dict()
    if detector_name is not None:
        kwargs['detector_name'] = detector_name
    if n_features is not None:
        kwargs['n_features'] = n_features
    unwarped = unwarp(image, template, **kwargs)

    if debug:
        cv2.imwrite('debug/template.png', template)
        cv2.imwrite('debug/image.png', image)
        cv2.imwrite('debug/unwarped.png', unwarped)

    schedule = find_booked_slots(unwarped)

    return schedule, unwarped


def print_schedule(schedule):
    print("<table>")
    for r in range(schedule.shape[0]):
        for c in range(schedule.shape[1]):
            print(schedule[r, c] and 'X' or '-', end=' ')
        print()
    print("</table>")


def parse_arguments(args):
    """Parse the command line arguments.

    Raise ValueError if the arguments are invalid or missing.
    """
    params = dict(
            detector='surf',
            n_features=5000
            )

    if '-v' in args:
        debug = True
        del args[args.index('-v')]
    if '-d' in args:
        index = args.index('-d')
        detector = args[index + 1]
        if detector not in ['orb', 'sift', 'surf']:
            raise ValueError('unknown detector: ' + detector + \
                             "(must be one of 'orb', 'sift', 'surf'")
        params['detector'] = detector
        del args[index + 1]
        del args[index]
    if '-n' in args:
        index = args.index('-n')
        params['n_features'] = int(args[index + 1])
        del args[index + 1]
        del args[index]

    if len(args) < 3:
        raise ValueError("not enough arguments")
    elif len(args) > 3:
        raise ValueError("too many arguments")

    params['template_file'] = args[0]
    params['input_file'] = args[1]
    params['output_file'] = args[2]

    return params


usage_message = """\
Usage: python {} [options] <template_image> <input_image> <output_image>
Options:
    -v                  enable debug mode
    -d [surf|orb|sift]  feature detector, default surf
    -n <integer>        number of features for orb and sift, default 5000
"""

def usage():
    import sys
    print(usage_message.format(sys.argv[0]))


def main():
    import sys
    try:
        params = parse_arguments(sys.argv[1:])
    except ValueError as e:
        print(e)
        print()
        usage()
        sys.exit(1)

    image = cv2.imread(params['input_file'], cv2.CV_LOAD_IMAGE_GRAYSCALE)
    template = cv2.imread(params['template_file'],
                           cv2.CV_LOAD_IMAGE_GRAYSCALE)

    if image is None:
        print("could no read image '" + params['input_file'] + "'")
        sys.exit(1)
    if template is None:
        print("could no read image '" + params['template_file'] + "'")
        sys.exit(1)

    import os.path
    if debug and not os.path.exists('debug'):
        import os
        os.mkdir('debug')

    detector_name = params['detector']
    n_features = params['n_features']
    schedule, unwarped = scan(image, template,
                              detector_name=detector_name,
                              n_features=n_features)

    print_schedule(schedule)

    highlighted = highlight_slots(unwarped)
    cv2.imwrite(params['output_file'], highlighted)


if __name__ == "__main__":
    main()
