from __future__ import print_function

import argparse
import logging
import sys

import cv2
import numpy as np

from fablab_schedule import config


logger = logging.getLogger(__name__)

debug = False


class ScheduleScanner:
    """Scan the wall schedule image for the booked slots."""

    def __init__(self, reference_image, detector_name="brisk",
                 n_features=1000):
        self.reference = reference_image
        self.detector_name = detector_name
        self.detector = self.make_detector(detector_name)
        self.matcher = self.make_matcher(detector_name)
        self.n_features = n_features
        self.ref_features = None
        self.schedule = None
        self.unwarped = None

    def make_detector(self, detector_name):
        """Construct the detector from its name.

        Parameters
        ----------
        detector_name: {"brisk", "orb", "sift", "surf"}

        Returns
        -------
        object implementing cv2.FeatureDetector

        Raises
        ------
        ValueError
            In case of invalid detector name.
        """
        if detector_name == "orb":
            return cv2.ORB_create(nfeatures=self.n_features, nlevels=4,
                                  scaleFactor=1.3, patchSize=25,
                                  edgeThreshold=25)
        elif detector_name == "sift":
            return cv2.xfeatures2d.SIFT_create(nfeatures=self.n_features)
        elif detector_name == "surf":
            return cv2.xfeatures2d.SURF_create()
        elif detector_name == "brisk":
            return cv2.BRISK_create()
        else:
            raise ValueError("unknown detector: {:s}".format(detector_name))

    def make_matcher(self, detector_name):
        """Construct the feature matcher adapted to the detector.

        Parameters
        ----------
        detector_name: {"brisk", "orb", "sift", "surf"}

        Returns
        -------
        cv2.BFMatcher
        """
        if detector_name in ["brisk", "orb"]:
            return cv2.BFMatcher(normType=cv2.NORM_HAMMING)
        else:
            return cv2.BFMatcher()

    def compute_features(self, image):
        """Compute keypoints and descriptors.

        Parameters
        ----------
        image: ndarray
            (M, N)

        Returns
        -------
        sequence of (keypoint, descriptor) pairs
        """
        mask = None
        keypoints, descriptors = self.detector.detectAndCompute(image, mask)
        return keypoints, descriptors

    def filter_matches_by_distance(self, matches, distance_ratio=0.75):
        """Remove weak matches, i.e. with dissimilar descriptors distances.

        Parameters
        ----------
        matches: sequence of cv2.DMatch pairs
        distance_ratio: float in [0, 1]
            Ratio over which the matches are considered weak and discarded.

        Returns
        -------
        sequence of cv2.DMatch pairs
            The descriptors distances ratio of each pair is less than
            `distance_ratio`.
        """
        return [m for m in matches
                if m[0].distance < m[1].distance * distance_ratio]

    def matches_to_points(self, matches, ref_keypoints, keypoints):
        """Extract the matching keypoints as numpy arrays.

        Parameters
        ----------
        matches: sequence of cv2.DMatch pairs
        ref_keypoints: sequence of reference keypoints objects
        keypoints: sequence of target keypoints objects

        Returns
        -------
        ref_points: ndarray
            (N, 2) array of np.float32
        points: ndarray
            (N, 2) array of np.float32
        """
        ref_points = np.float32([ref_keypoints[m[0].queryIdx].pt
                                 for m in matches])
        points = np.float32([keypoints[m[0].trainIdx].pt for m in matches])
        return ref_points, points

    def find_matching_points(self, reference_features, features):
        """Find the points whose feature descriptors match.

        Parameters
        ----------
        reference_features: sequence of (keypoint, descriptor) pairs
        features: sequence of (keypoint, descriptor) pairs

        Returns
        -------
        ref_points: ndarray
            (N, 2) array of np.float32
        points: ndarray
            (N, 2) array of np.float32
        """
        ref_keypoints, ref_descriptors = reference_features
        keypoints, descriptors = features

        # ask for the two best matches at most
        match_count = 2
        matches = self.matcher.knnMatch(ref_descriptors, descriptors,
                                        match_count)
        # remove weak matches, i.e. only one match found
        matches = [m for m in matches if len(m) == match_count]
        matches = self.filter_matches_by_distance(matches, distance_ratio=0.75)

        ref_points, points = self.matches_to_points(matches, ref_keypoints,
                                                    keypoints)
        return ref_points, points

    def find_transformation(self, ref_points, points):
        """Find the transformation matrix mapping two feature sets.

        Parameters
        ----------
        ref_points: ndarray
            (N, 2) array of np.float32
        points: ndarray
            (N, 2) array of np.float32

        Returns
        -------
        ndarray
            The (3, 3) transformation matrix that maps the feature sets.
        """
        method = cv2.RANSAC
        inlier_threshold = 7    # only effective with RANSAC
        #  method = cv2.LMEDS
        transformation, _ = cv2.findHomography(ref_points, points, method,
                                               inlier_threshold)
        return transformation

    def unwarp(self, image, transformation):
        """Apply an inverse perspective transformation to `image`.

        Parameters
        ----------
        image: ndarray
            (M, N) image.
        transformation: ndarray
            (3, 3) forward transformation matrix.

        Returns
        -------
        unwarped: ndarray
            (M, N) unwarped image.
        """
        unwarped = cv2.warpPerspective(image, transformation,
                                       self.reference.T.shape, None,
                                       cv2.WARP_INVERSE_MAP)
        return unwarped

    def scan(self, image):
        """Scan the image for the schedule.

        Parameters
        ----------
        image: ndarray
            (M, N) image

        Returns
        -------
        schedule: array_like, int
            A 2-dimensional table of boolean values indicating the occupancy of
            the schedule. An entry is `True` if booked, `False` otherwise.
        """
        if self.ref_features is None:
            self.ref_features = self.compute_features(self.reference)
        features = self.compute_features(image)

        ref_points, points = self.find_matching_points(self.ref_features,
                                                       features)
        transformation = self.find_transformation(ref_points, points)

        self.unwarped = self.unwarp(image, transformation)

        slot_scanner = SlotScanner()
        self.schedule = slot_scanner.find_booked_slots(self.unwarped)

        return self.schedule


class SlotScanner:

    def __init__(self):
        conf = config.get()
        self.table_blueprint = TableBlueprint.from_config(conf)
        self.booked_slots = None

    def compute_roughness(self, image):
        dx, dy = np.gradient(image)
        return np.mean(np.sqrt(dx**2 + dy**2))

    def is_card_absent(self, slot_image, threshold):
        # A card is absent if the roughness is low.
        return self.compute_roughness(slot_image) < threshold

    def compute_roughness_threshold(self, mean_intensity):
        """Compute a roughness threshold adjusted to the mean intensity level.

        Parameters
        ----------
        mean_intensity: int
            Mean intensity level of the reference image.

        Returns
        -------
        float
            The adapted roughness threshold.
        """
        reference_mean_intensity_level = 150
        threshold_at_reference = 2.5
        threshold = threshold_at_reference \
            * (mean_intensity / reference_mean_intensity_level)
        return threshold

    def find_booked_slots(self, image):
        """Find which slots are booked in the reference image of the schedule.

        Parameters
        ----------
        image : ndarray
            (M, N) unwarped image of the schedule table.

        Returns
        -------
        schedule : array_like, bool
            A 2-dimensional table of boolean values indicating the occupancy of
            the schedule. An entry is `True` if booked, `False` otherwise.
        """
        image_float = image.astype(float)
        mean_intensity = image_float.mean()
        threshold = self.compute_roughness_threshold(mean_intensity)
        table = self.table_blueprint
        schedule = np.zeros(table.shape[:2], dtype=bool)
        for row_index in range(table.n_rows):
            for col_index in range(table.n_cols):
                r, c = table.slot_offsets[row_index, col_index]
                r_min = r - table.slot_radius
                r_max = r + table.slot_radius
                c_min = c - table.slot_radius
                c_max = c + table.slot_radius
                slot = image_float[r_min:r_max, c_min:c_max]
                if self.is_card_absent(slot, threshold):
                    schedule[row_index, col_index] = True
        return schedule


def cartesian_product(x, y):
    return [[(valx, valy) for valy in y] for valx in x]


class TableBlueprint:

    def __init__(self, slot_offsets, slot_radius):
        self.slot_offsets = np.array(slot_offsets, dtype=int)
        self.shape = self.slot_offsets.shape
        self.n_rows, self.n_cols, _ = self.shape
        self.slot_radius = slot_radius

    @staticmethod
    def from_config(conf):
        row_offsets = conf["row_offsets"]
        column_offsets = conf["column_offsets"]
        slot_offsets = TableBlueprint.make_slot_offsets(row_offsets,
                                                        column_offsets)
        slot_radius = int(conf["slot_size"] / 2)
        return TableBlueprint(slot_offsets, slot_radius)

    @staticmethod
    def make_slot_offsets(row_offsets, column_offsets):
        return cartesian_product(row_offsets, column_offsets)


def highlight_slots(image, table_blueprint):
    """Highlight the slots on the image for visualisation purpose.

    Parameters
    ----------
    image : ndarray
        (M, N) image of the schedule.
    table_blueprint: object
        A TableBlueprint object giving the features of the table.

    Returns
    -------
    highlighted : ndarray
        (M, N) image with highlighted slots.
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


def read_image_grayscale(filename):
    return cv2.imread(filename, 0)


def parse_arguments():
    """Parse the command line arguments.

    Returns
    -------
    dict
        The parameters.
    """
    global debug

    description = "Scan the FabLab wall schedule"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="display debug information")
    parser.add_argument("-d", "--detector",
                        choices=["brisk", "orb", "sift", "surf"],
                        default="brisk",
                        help="select feature detector (default: %(default)s)")
    parser.add_argument("-f", "--features", type=int, default=5000,
                        help="number of features to detect "
                             "(default: %(default)d)")
    parser.add_argument("-o", "--output",
                        help="output image with detected slots highlighted")
    parser.add_argument("reference", help="reference image")
    parser.add_argument("input", help="input image")

    args = parser.parse_args()
    if args.verbose:
        debug = True
    params = dict(
        detector=args.detector,
        n_features=args.features,
        reference_file=args.reference,
        input_file=args.input,
        output_file=args.output,
    )

    return params


def print_schedule(schedule):
    table_string = "<table>\n"
    for r in range(schedule.shape[0]):
        for c in range(schedule.shape[1]):
            table_string += "X" if schedule[r, c] else "-"
            table_string += " "
        table_string += "\n"
    table_string += "</table>"
    print(table_string)


def scan(reference_file, input_file, detector, n_features=1000):
    reference = read_image_grayscale(reference_file)
    image = read_image_grayscale(input_file)

    if reference is None:
        logger.error("cannot read image '{:s}'".format(reference_file))
        sys.exit(1)
    if image is None:
        logger.error("cannot read image '{:s}'".format(input_file))
        sys.exit(1)

    scanner = ScheduleScanner(reference, detector, n_features)
    schedule = scanner.scan(image)

    return schedule, scanner.unwarped


def main():
    params = parse_arguments()

    reference_file = params['reference_file']
    input_file = params['input_file']
    detector = params['detector']
    n_features = params['n_features']
    schedule, unwarped = scan(reference_file, input_file, detector, n_features)
    print_schedule(schedule)
    if params['output_file'] is not None:
        table_blueprint = TableBlueprint.from_config(config.get())
        highlighted = highlight_slots(unwarped, table_blueprint)
        cv2.imwrite(params['output_file'], highlighted)


if __name__ == "__main__":
    main()
