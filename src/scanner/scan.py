from __future__ import print_function

import sys

import cv2
import numpy as np


def rectify(image, reference, detector='surf', n_features=5000, debug=False):
    """Transform an image to fit the reference image.

    Parameters
    ----------
    image : (M, N)
        Image to rectify.
    reference : (P, Q)
        Reference image.
    detector: string, optional
        The feature detector to be used.
    n_features: int, optional
        The number of features to use.
    debug : bool, optional
        Displays some debug infos and saves intermediate results as images.

    Returns
    -------
    recified : (M', N')
        The rectified image.
    """
    detector_name = detector
    if detector == 'orb':
        detector = cv2.ORB(nfeatures=n_features)
        matcher = cv2.BFMatcher(normType=cv2.NORM_HAMMING, crossCheck=True)
    elif detector == 'sift':
        detector = cv2.SIFT(nfeatures=n_features)
        matcher = cv2.BFMatcher(crossCheck=True)
    elif detector == 'surf':
        detector = cv2.SURF()
        matcher = cv2.BFMatcher(crossCheck=True)
    else:
        raise ValueError('unknown detector: {:s}'.format(detector) +
                         '(should be one of "orb", "sift", "surf"')

    if debug:
        print('detector = ' + detector_name)
        if detector_name != 'surf':
            print('n_features = ' + str(n_features))

    keypoints1, descriptors1 = detector.detectAndCompute(reference, None)
    keypoints2, descriptors2 = detector.detectAndCompute(image, None)

    matches = matcher.match(descriptors1, descriptors2)
    keypoints1 = np.array([keypoints1[int(m.queryIdx)].pt for m in matches],
            dtype=np.float32)
    keypoints2 = np.array([keypoints2[int(m.trainIdx)].pt for m in matches],
            dtype=np.float32)

    transform_matrix, mask = cv2.findHomography(keypoints1, keypoints2,
            cv2.RANSAC, 7)
    inliers = mask.ravel().tolist()

    rectified = cv2.warpPerspective(image, transform_matrix, reference.T.shape,
            None, cv2.WARP_INVERSE_MAP)

    if debug:
        try:
            import matplotlib.pyplot as plt
            from skimage.feature import plot_matches
            fig, ax = plt.subplots()
            seq = np.arange(len(keypoints1))[:, np.newaxis]
            matches = np.tile(seq, (1, 2))
            kp1 = np.roll(keypoints1, 1, axis=1)
            kp2 = np.roll(keypoints2, 1, axis=1)
            plot_matches(ax, reference, image, kp1, kp2, matches)
            ax.axis('off')
            plt.savefig('debug/matched.png')
        except:
            pass

    return rectified


def find_occupation(image, debug=False):
    """Find which slots are booked in the occupation table.

    Parameters
    ----------
    image : (M, N)
        Aligned image of the occupation table.
    debug : bool, optional
        Displays some debug infos and saves intermediate results as images.

    Returns
    -------
    occupation : (N_MACHINES, N_SLOTS), bool
        Occupation matrix (True if slot occupied).
    output_image:
        Image with detected slots highlighted.
    """
    n_machines = 7
    n_slots = 9
    occupation = np.zeros((n_machines, n_slots), dtype=bool)

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

    image_float = image.astype(float)

    radius = 15     # radius of a square patch encompassing a slot

    threshold = 2.5   # threshold at mean intensity level == 150
    # Adapt the threshold to the image mean intensity level.
    mean_intensity = image_float.mean()
    threshold = threshold * (mean_intensity / 150)

    if debug:
        print("roughness threshold = {:.2f}".format(threshold))
    
    # Measure the slot roughness from which we deduce if a card is present.
    def roughness(patch):
        grad = np.gradient(patch)
        return np.mean(np.sqrt(grad[0]**2 + grad[1]**2))

    # Small roughness level means card absent, i.e. slot booked.
    # High roughness level means card present, i.e. not booked..
    def is_booked(patch):
        return roughness(patch) < threshold

    if debug:
        slot_roughness = np.zeros((n_machines, n_slots))

    for machine_index in range(n_machines):
        for slot_index in range(n_slots):
            r, c = slot_position[machine_index, slot_index]
            patch = image_float[r-radius:r+radius, c-radius:c+radius]
            if is_booked(patch):
                occupation[machine_index, slot_index] = True
            if debug:
                slot_roughness[machine_index, slot_index] = roughness(patch)

    if debug:
        np.set_printoptions(precision=2)
        print(slot_roughness)

    # Highlight the slots on the image for visualisation
    slot_mask = np.ones_like(image, dtype=bool)
    for m in range(n_machines):
        for s in range(n_slots):
            r, c = slot_position[m, s]
            patch = image_float[r-radius:r+radius, c-radius:c+radius]
            # create a mask for the slot
            slot_mask[r-radius:r+radius, c-radius:c+radius] = False
    output_image = image.copy()
    output_image[slot_mask] = 0.5 * output_image[slot_mask]

    return occupation, output_image


def scan_table(image, banner, detector=None, n_features=None, debug=False):
    """Scan the image for the status of the slots in the occupation table.

    Parameters
    ----------
    image : (M, N, 3)
        Image to scan.
    banner : (M, N, 3)
        Reference image of the banner.
    detector: string, optional
        The feature detector used to rectify the image.
    n_features: string, optional
        The number of features for the detector.
    debug : bool, optional
        Displays some debug infos and saves intermediate results as images.

    Returns
    -------
    table : (N_MACHINES, N_SLOTS), bool
        Boolean matrix indicating the booking status of the machines.
    """
    kwargs = dict(debug=debug)
    if detector is not None:
        kwargs['detector'] = detector
    if n_features is not None:
        kwargs['n_features'] = n_features
    rectified = rectify(image, banner, **kwargs)

    if debug:
        cv2.imwrite('debug/banner.png', banner)
        cv2.imwrite('debug/image.png', image)
        cv2.imwrite('debug/rectified.png', rectified)

    occupation, output_image = find_occupation(rectified, debug=debug)

    return occupation, output_image


def print_occupation(occupation):
    print("<table>")
    for r in range(occupation.shape[0]):
        for c in range(occupation.shape[1]):
            print(occupation[r, c] and 'X' or '-', end=' ')
        print()
    print("</table>")


def parse_arguments():
    """Parse the command line arguments.

    Raise ValueError if the arguments are invalid or missing.
    """
    args = sys.argv[1:]

    params = dict(debug=False,
                  detector='surf',
                  n_features=5000)

    if '-d' in args:
        params['debug'] = True
        del args[args.index('-d')]
    if '-f' in args:
        index = args.index('-f')
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

    params['input_file'] = args[0]
    params['banner_file'] = args[1]
    params['output_file'] = args[2]

    return params


usage_message = """\
Usage: python scan.py [options] input_image banner output_image
Options:
    -d                  output debug messages and images
    -f [surf|orb|sift]  feature detector, default surf
    -n <integer>        number of features for orb and sift, default 5000
"""

def usage():
    print(usage_message)


def main():
    try:
        params = parse_arguments()
    except ValueError as e:
        print(e)
        print()
        usage()
        sys.exit(1)

    image = cv2.imread(params['input_file'], cv2.CV_LOAD_IMAGE_GRAYSCALE)
    banner = cv2.imread(params['banner_file'], cv2.CV_LOAD_IMAGE_GRAYSCALE)

    if image is None:
        print("could no read image '" + params['input_file'] + "'")
        sys.exit(1)
    if banner is None:
        print("could no read image '" + params['banner_file'] + "'")
        sys.exit(1)

    import os.path
    if params['debug'] and not os.path.exists('debug'):
        import os
        os.mkdir('debug')

    detector = params['detector']
    n_features = params['n_features']
    debug = params['debug']
    occupation, output_image = scan_table(image, banner, detector=detector,
                                          n_features=n_features,
                                          debug=debug)
    print_occupation(occupation)
    cv2.imwrite(params['output_file'], output_image)


if __name__ == "__main__":
    main()
