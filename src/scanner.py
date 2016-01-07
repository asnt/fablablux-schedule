from __future__ import print_function

import cv2
import numpy as np
from skimage.color import rgb2gray
from skimage.io import imread, imsave


def rectify(image, reference, debug=False):
    """Transform an image to fit the reference image.

    Parameters
    ----------
    image : (M, N)
        Image to rectify.
    reference : (P, Q)
        Reference image.
    transform: optional
        The transform type to be used. ProjectiveTransform by default.
    debug : bool, optional
        Displays some debug infos and saves intermediate results as images.

    Returns
    -------
    recified : (M', N')
        Rectified image.
    model : transform type 
        Instance of the geometric transformation used.
    """
    detector = cv2.ORB(nfeatures=2000)
    keypoints1, descriptors1 = detector.detectAndCompute(reference, None)
    keypoints2, descriptors2 = detector.detectAndCompute(image, None)

    matcher = cv2.BFMatcher(normType=cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(descriptors1, descriptors2)
    keypoints1 = np.array([keypoints1[int(m.queryIdx)].pt for m in matches],
            dtype=np.float32)
    keypoints2 = np.array([keypoints2[int(m.trainIdx)].pt for m in matches],
            dtype=np.float32)

    transform_matrix, mask = cv2.findHomography(keypoints1, keypoints2,
            cv2.RANSAC, 0.1)
    inliers = mask.ravel().tolist()

    rectified = cv2.warpPerspective(image, transform_matrix, image.T.shape,
            None, cv2.WARP_INVERSE_MAP)

    if debug:
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
    """
    n_machines = 7
    n_slots = 9
    occupation = np.zeros((n_machines, n_slots), dtype=bool)

    # Position of the top-left slot of the table
    r0, c0 = 140, 115
    # Distance to subsequent rows (vertical direction)
    d_rows = np.array([0, 62.5, 125, 220, 285, 375, 465])
    d_rows = d_rows / 2 # using half resolution image
    # Distance to subsequent cols (horizontal direciton)
    d_cols = 78 * np.arange(n_slots)
    d_cols = d_cols / 2 # using half resolution image
    # Absolution position of the slots
    row_tile = np.tile(d_rows[:, np.newaxis], (1, n_slots))
    col_tile = np.tile(d_cols, (n_machines, 1))
    pos = np.dstack((r0 + row_tile, c0 + col_tile))


    threshold = 2.5   # threshold at mean intensity level == 150
    radius = 15     # radius of a square patch encompassing a slot
    image_float = image.astype(float)
    # Adapt the threshold to the image mean intensity level.
    mean_intensity = image_float.mean()
    threshold = threshold * (mean_intensity / 150)
    print(threshold)
    # Measure of the slot roughness. Much roghness means the card is present,
    # few roughness the card is not there.
    def roughness(patch):
        grad = np.gradient(patch)
        return np.mean(np.sqrt(grad[0]**2 + grad[1]**2))
    # Helper function to check slot status.
    def is_booked(patch):
        return roughness(patch) < threshold
    for m in range(n_machines):
        for s in range(n_slots):
            r, c = pos[m, s]
            patch = image_float[r-radius:r+radius, c-radius:c+radius]
            # If the patch is smooth enough, it means there is no card, i.e.
            # it is booked.
            if roughness(patch) < threshold:
                occupation[m, s] = True

    if debug:
        slot_mask = np.ones_like(image, dtype=bool)
        roughness_values = []
        for m in range(n_machines):
            for s in range(n_slots):
                r, c = pos[m, s]
                # save roughness value
                patch = image_float[r-radius:r+radius, c-radius:c+radius]
                roughness_values.append(roughness(patch))
                # mask slots out
                slot_mask[r-radius:r+radius, c-radius:c+radius] = False
        image_slots = image.copy()
        image_slots[slot_mask] = 0.5 * image_slots[slot_mask]
        np.set_printoptions(precision=3)
        print(np.reshape(np.array(roughness_values), (n_machines, n_slots)))
        imsave('debug/slots.png', image_slots)

    return occupation


def scan_table(image, banner, debug=False):
    """Scan the image for the status of the slots in the occupation table.

    Parameters
    ----------
    image : (M, N, 3)
        Image to scan.
    banner : (M, N, 3)
        Reference image of the banner.
    debug : bool, optional
        Displays some debug infos and saves intermediate results as images.

    Returns
    -------
    table : (N_MACHINES, N_SLOTS), bool
        Boolean matrix indicating the booking status of the machines.
    """
    rectified = rectify(image, banner, debug)

    if debug:
        imsave('debug/banner.jpg', banner)
        imsave('debug/image.jpg', image)
        imsave('debug/rectified.jpg', rectified)

    occupation = find_occupation(rectified, debug)

    return occupation


def print_occupation(occupation):
    for r in range(occupation.shape[0]):
        for c in range(occupation.shape[1]):
            print(occupation[r, c] and 'X' or '-', end=' ')
        print()


if __name__ == "__main__":
    # usage example: python scanner.py [-d] image banner
    import sys
    args = sys.argv[1:]
    if '-d' in args:
        debug = True
        del args[args.index('-d')]
    else:
        debug = False
    image = cv2.imread(args[0], cv2.CV_LOAD_IMAGE_GRAYSCALE)
    banner = cv2.imread(args[1], cv2.CV_LOAD_IMAGE_GRAYSCALE)

    import os.path
    if debug and not os.path.exists('debug'):
        import os
        os.mkdir('debug')

    occupation = scan_table(image, banner, debug=debug)
    print_occupation(occupation)
