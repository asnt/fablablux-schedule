from __future__ import print_function

import sys

import cv2
import numpy as np

from fablab_schedule import config


debug = False


def scan(image, template, detector_name='surf', n_features=5000):
    """Scan the schedule from the warped image.

    Parameters
    ----------
    image : (M, N, 3)
        Warped image of the schedule table.
    template : (M, N, 3)
        Non-warped template image of the schedule table.
    detector_name: string, optional
        The name of the feature detector to use. Default, 'surf'.
    n_features: string, optional
        The number of features for the detector. Does not apply to the SURF
        detector. Default, 5000.

    Returns
    -------
    schedule : (N_MACHINES, N_SLOTS), bool
        Boolean matrix indicating the booking status of the machines.
    unwarped : (M, N)
        Unwarped image.
    """
    unwarped = unwarp(image, template, detector_name, n_features)

    if debug:
        import os.path
        if not os.path.exists('debug'):
            import os
            os.mkdir('debug')
        cv2.imwrite('debug/template.png', template)
        cv2.imwrite('debug/image.png', image)
        cv2.imwrite('debug/unwarped.png', unwarped)

    table_schema = TableBlueprint.from_config(config.get())
    schedule = find_booked_slots(unwarped, table_schema)

    return schedule, unwarped


def unwarp(image, template, detector_name, n_features=5000):
    """Transform an image to fit the template.

    Parameters
    ----------
    image : (M, N)
        Image to rectify.
    template : (P, Q)
        Template image.
    detector_name : string
        The feature detector to be used.
    n_features : int, optional
        The number of features to use. Default 5000. Does not apply to the
        SURF detector.

    Returns
    -------
    unwarped : (M', N')
        The unwarped image.
    """
    detector, matcher = make_detector_and_matcher(detector_name, n_features)

    mask = None
    keypoints1, descriptors1 = detector.detectAndCompute(template, mask)
    keypoints2, descriptors2 = detector.detectAndCompute(image, mask)

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


def make_detector_and_matcher(detector_name, n_features):
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
        matcher = cv2.BFMatcher(crossCheck=True)
    else:
        raise ValueError('unknown detector: {:s}'.format(detector) +
                         '(should be one of "orb", "sift", "surf"')

    return detector, matcher


def find_booked_slots(image, table_blueprint):
    """Find which slots are booked in the image of the schedule table.

    Parameters
    ----------
    image : (M, N)
        Aligned image of the schedule table.
    table_blueprint :
        A TableBlueprint object giving the features of the table. 

    Returns
    -------
    schedule : (N_MACHINES, N_SLOTS), bool
        Schedule matrix (True if slot scheduled).
    """
    image_float = image.astype(float)
    mean_intensity = image_float.mean()
    roughness_threshold = compute_roughness_threshold(mean_intensity)

    if debug:
        print("roughness threshold = {:.2f}".format(roughness_threshold))
    
    def roughness(image_patch):
        dx, dy = np.gradient(image_patch)
        return np.mean(np.sqrt(dx**2 + dy**2))

    def is_booked(slot_image):
        # A slot is booked if the card is absent, i.e. the roughness is low.
        return roughness(slot_image) < roughness_threshold

    if debug:
        slot_roughness = np.zeros(table_blueprint.shape)

    table = table_blueprint
    schedule = np.zeros(table.shape, dtype=bool)
    for row_index in range(table.n_rows):
        for col_index in range(table.n_cols):
            r, c = table.slot_offsets[row_index, col_index]
            r_min = r - table.slot_radius
            r_max = r + table.slot_radius
            c_min = c - table.slot_radius
            c_max = c + table.slot_radius
            slot = image_float[r_min:r_max, c_min:c_max]
            if is_booked(slot):
                schedule[row_index, col_index] = True
            if debug:
                slot_roughness[row_index, col_index] = roughness(patch)

    if debug:
        np.set_printoptions(precision=2)
        print(slot_roughness)

    return schedule


def compute_roughness_threshold(mean_intensity):
    """Compute a roughness threshold adjusted to the given mean intensity."""
    reference_mean_intensity_level = 150
    roughness_threshold_at_reference = 2.5
    roughness_threshold = roughness_threshold_at_reference * \
                          (mean_intensity / reference_mean_intensity_level)
    return roughness_threshold


class TableBlueprint:

    def __init__(self, slot_offsets, slot_radius):
        self.slot_offsets = np.array(slot_offsets)
        self.shape = self.slot_offsets.shape
        self.n_rows, self.n_cols, __ = self.shape
        self.slot_radius = slot_radius

    @staticmethod
    def from_config(conf):
        row_offsets = conf["row_offsets"]
        column_offsets = conf["column_offsets"]
        slot_offsets = self._make_slot_offsets(row_offsets, column_offsets)
        slot_radius = int(conf["slot_size"] / 2)
        return TableBlueprint(slot_offsets, slot_radius)

    def _make_slot_offsets(row_offsets, column_offsets):
        return cartesian_product(row_offsets, column_offsets)


def cartesian_product(x, y):
    return [[[valx, valy] for valy in y] for valx in x]


def highlight_slots(image, table_blueprint):
    """Highlight the slots on the image for visualisation purpose.

    Parameters
    ----------
    image : (M, N)
        Image of the schedule.
    table_blueprint :
        A TableBlueprint object giving the features of the table. 

    Returns
    -------
    highlighted : (M, N)
        Image with highlighted slots.
    """
    slot_mask = np.ones_like(image, dtype=bool)
    for m in range(table_blueprint.n_rows):
        for s in range(table_blueprint.n_cols):
            r, c = table_blueprint.slot_offsets[m, s]
            r_min = r - table_blueprint.slot_radius
            r_max = r + table_blueprint.slot_radius
            c_min = c - table_blueprint.slot_radius
            c_max = c + table_blueprint.slot_radius
            slot_mask[r_min:r_max, c_min:c_max] = False

    highlighted = image.copy()
    highlighted[slot_mask] = 0.5 * highlighted[slot_mask]

    return highlighted


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

    detector_name = params['detector']
    n_features = params['n_features']
    schedule, unwarped = scan(image, template, detector_name, n_features)

    print_schedule(schedule)

    table_blueprint = TableBlueprint.from_config(config.get())
    highlighted = highlight_slots(unwarped, table_blueprint)
    cv2.imwrite(params['output_file'], highlighted)


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


def print_schedule(schedule):
    print("<table>")
    for r in range(schedule.shape[0]):
        for c in range(schedule.shape[1]):
            print(schedule[r, c] and 'X' or '-', end=' ')
        print()
    print("</table>")


if __name__ == "__main__":
    main()
