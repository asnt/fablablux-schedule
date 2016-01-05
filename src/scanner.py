import matplotlib.pyplot as plt
import numpy as np
import scipy.ndimage as ndi
import scipy.ndimage.filters
import skimage as ski
import skimage.io
import skimage.morphology
from skimage.color import rgb2gray
from skimage.feature import (match_descriptors, corner_harris, corner_peaks,
                             ORB, plot_matches)
from skimage.io import imread
from skimage.measure import ransac
from skimage.transform import warp, ProjectiveTransform


def match(img1, img2, debug=False):
    """Match keypoints in two images.

    Parameters
    ----------
    img1 : (M, N)
        The first grayscale image.
    img2 : (P, Q)
        The second grayscale image.

    Returns
    -------
    (keypoints1, keypoints2) : (K1, 2), (K2, 2)
        Matched keypoints from the two images.
    """
    descriptor_extractor = ORB(n_keypoints=500, harris_k=0.15)

    descriptor_extractor.detect_and_extract(img1)
    keypoints1 = descriptor_extractor.keypoints
    descriptors1 = descriptor_extractor.descriptors

    descriptor_extractor.detect_and_extract(img2)
    keypoints2 = descriptor_extractor.keypoints
    descriptors2 = descriptor_extractor.descriptors

    matches = match_descriptors(descriptors1, descriptors2, cross_check=True)

    return keypoints1[matches[:, 0]], keypoints2[matches[:, 1]]


def fit_transform(keypoints1, keypoints2, transform):
    """Determine the transform that maps two sets of matched keypoints.

    Parameters
    ----------
    keypoints1 : (N, 2)
        First set of keypoints.
    keypoints2 : (N, 2)
        Second set of keypoints.
    transform:
        The transform type to be used.

    Returns
    -------
    object
        An instance of the transform type.
    inliers: (N,)
        A boolean array indicating inlier keypoints. 
    """
    model, inliers = ransac((keypoints1, keypoints2), transform, 7, 1,
            max_trials=10000)
    return model, inliers


def rectify(image, reference, transform=ProjectiveTransform, debug=False):
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
    keypoints = match(reference, image)
    model, inliers = fit_transform(*keypoints, transform)
    rectified = warp(image.T, model).T

    if debug:
        from skimage.feature import plot_matches
        fig, ax = plt.subplots()
        seq = np.arange(len(keypoints[0]))[:, np.newaxis]
        matches = np.tile(seq, (1, 2))
        plot_matches(ax, reference, image, keypoints[0], keypoints[1], matches)
        ax.axis('off')
        plt.savefig('debug/matched.png')

    if debug:
        from skimage.feature import plot_matches
        fig, ax = plt.subplots()
        kp1 = keypoints[0][inliers, :]
        kp2 = keypoints[1][inliers, :]
        seq = np.arange(len(kp1))[:, np.newaxis]
        matches = np.tile(seq, (1, 2))
        plot_matches(ax, reference, image, kp1, kp2, matches)
        ax.axis('off')
        plt.savefig('debug/matched-inliers.png')

    return rectified, model


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

    # Check slot status.
    def roughness(patch):
        grad = np.gradient(patch)
        return np.mean(np.sqrt(grad[0]**2 + grad[1]**2))
    threshold = 0.015
    radius = 15
    for m in range(n_machines):
        for s in range(n_slots):
            r, c = pos[m, s]
            patch = image[r-radius:r+radius, c-radius:c+radius]
            # If the patch is smooth enough, it means there is no card, i.e.
            # it is booked.
            if roughness(patch) < threshold:
                occupation[m, s] = True

    if debug:
        slot_mask = np.zeros_like(image)
        roughness_values = []
        for m in range(n_machines):
            for s in range(n_slots):
                r, c = pos[m, s]
                # save roughness value
                patch = image[r-radius:r+radius, c-radius:c+radius]
                roughness_values.append(roughness(patch))
                # set the mas
                slot_mask[r-radius:r+radius, c-radius:c+radius] *= 2
        image_slots = image.copy()
        image_slots = slot_mask * image_slots
        np.set_printoptions(precision=3)
        print(np.reshape(np.array(roughness_values), (n_machines, n_slots)))
        ski.io.imsave('debug/slots.png', image_slots)

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
    image_gray = rgb2gray(image)
    banner_gray = rgb2gray(banner)

    transform = ProjectiveTransform
    rectified, model = rectify(image_gray, banner_gray, transform, debug)

    if debug:
        ski.io.imsave('debug/banner-gray.jpg', banner_gray)
        ski.io.imsave('debug/image-gray.jpg', image_gray)
        ski.io.imsave('debug/rectified.jpg', rectified)
        print('transformation matrix:', model.params)

    occupation = find_occupation(rectified, debug)
    if debug:
        for r in range(occupation.shape[0]):
            for c in range(occupation.shape[1]):
                print(occupation[r, c] and 'X' or '-', end=' ')
            print()

    return occupation


def pairwise(iterable):
    """s0, s1, s2, s3,... -> (s0, s1), (s2, s3), ..."""
    a = iter(iterable)
    return zip(a, a)


def find_slots_limits(image, compute_std=True, debug=False):
    if compute_std:
        row_std = image.std(axis=0).mean(axis=1)
        #row_std = image.std(axis=0)
    else:
        row_std = image
    row_plateau = row_std > 10
    row_transitions = abs(row_plateau[1:] - row_plateau[:-1])
    row_transitions = np.nonzero(row_transitions)[0]
    n_transitions = len(row_transitions)
    if debug:
        fig = plt.figure()
        plt.plot(image)
        fig.savefig('debug/slots_row.png')
    # ensure an even count of entries
    row_transitions = row_transitions[:n_transitions - n_transitions % 2]
    return list(pairwise(row_transitions))


def find_banner_limits(image, debug=False):
    """Find the limits of the banner.

    Parameters
    ----------
    image : (M, N)
    debug : bool, optional
        Displays some debug infos and saves intermediate results as images.
        
    Returns
    -------
    (top, bottom, left, right) : int
        Limits of the banner.
    """
    #row_mean = image.mean(axis=2).mean(axis=1)
    row_mean = image.mean(axis=1)
    #thresh = 75
    thresh = 100
    transitions = np.nonzero(np.diff(row_mean < thresh))[0]
    if debug:
        print("row_mean transitions", transitions)
        print("row_mean transitions[:10]", transitions[:10])
    header_r0 = transitions[0]
    i = 1
    while transitions[i] - transitions[i-1] < 500 / 4:
        i += 1
    header_r1 = transitions[i-1]

    if debug:
        print('header rows:', (header_r0, header_r1))
        ski.io.imsave('debug/header_rows.jpg', image[header_r0:header_r1, :])

    # find horizontal limits
    col_mean = image[header_r0:header_r1, :].mean(axis=0)
    #thresh = 75
    thresh = 100
    if debug:
        print("header col_mean", col_mean)
    dark_cols = np.nonzero(col_mean < thresh)[0]

    if debug:
        print("header dark cols", dark_cols)

    header_c0 = dark_cols[0]
    header_c1 = dark_cols[-1]

    if debug:
        print('header cols:', (header_c0, header_c1))
        ski.io.imsave('debug/header.jpg', image[header_r0:header_r1,
            header_c0:header_c1])

    return header_r0, header_r1, header_c0, header_c1


if __name__ == "__main__":
    # usage example: python scanner.py [-d] image banner
    import sys
    args = sys.argv[1:]
    if '-d' in args:
        debug = True
        del args[args.index('-d')]
    else:
        debug = False
    image = ski.io.imread(args[0])
    banner = ski.io.imread(args[1])

    import os.path
    if debug and not os.path.exists('debug'):
        import os
        os.mkdir('debug')

    scan_table(image, banner, debug=debug)
