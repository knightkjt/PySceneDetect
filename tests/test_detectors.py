# -*- coding: utf-8 -*-
#
#         PySceneDetect: Python-Based Video Scene Detector
#   ---------------------------------------------------------------
#     [  Site: http://www.bcastell.com/projects/PySceneDetect/   ]
#     [  Github: https://github.com/Breakthrough/PySceneDetect/  ]
#     [  Documentation: http://pyscenedetect.readthedocs.org/    ]
#
# Copyright (C) 2014-2021 Brandon Castellano <http://www.bcastell.com>.
#
# PySceneDetect is licensed under the BSD 3-Clause License; see the included
# LICENSE file, or visit one of the following pages for details:
#  - https://github.com/Breakthrough/PySceneDetect/
#  - http://www.bcastell.com/projects/PySceneDetect/
#
# This software uses Numpy, OpenCV, click, tqdm, simpletable, and pytest.
# See the included LICENSE files or one of the above URLs for more information.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

""" PySceneDetect Scene Detection Tests

These tests ensure that the detection algorithms deliver consistent
results by using known ground truths of scene cut locations in the
test case material.
"""

# Standard project pylint disables for unit tests using pytest.
# pylint: disable=no-self-use, protected-access, multiple-statements, invalid-name
# pylint: disable=redefined-outer-name

# PySceneDetect Library Imports
from scenedetect import SceneManager, FrameTimecode, StatsManager
from scenedetect.video_stream import VideoStream
from scenedetect.scene_detector import SceneDetector
from scenedetect.detectors import ContentDetector
from scenedetect.detectors import ThresholdDetector
from scenedetect.detectors import AdaptiveDetector
from scenedetect.backends.opencv import VideoStreamCv2

from typing import Type


# Test case ground truth format: (threshold, [scene start frame])
TEST_MOVIE_CLIP_GROUND_TRUTH_CONTENT = [
    (30, [1198, 1226, 1260, 1281, 1334, 1365, 1697, 1871]),
    (27, [1198, 1226, 1260, 1281, 1334, 1365, 1590, 1697, 1871])
]

#
def create_detector(detector_type: Type, video: VideoStream) -> SceneDetector:
    """ Factory function for creating a detector.  Required since some detectors require
    additional parameters. Used so all have the same signature, thus a single test case
    can be written over multiple detectors.
    """
    if detector_type == AdaptiveDetector:
        return detector_type(video)
    return detector_type()


def test_content_detector(test_movie_clip):
    """ Test SceneManager with VideoStreamCv2 and ContentDetector. """
    for threshold, start_frames in TEST_MOVIE_CLIP_GROUND_TRUTH_CONTENT:
        video = VideoStreamCv2(test_movie_clip)
        sm = SceneManager()
        sm.add_detector(ContentDetector(threshold=threshold))

        video_fps = video.frame_rate
        start_time = FrameTimecode('00:00:50', video_fps)
        end_time = FrameTimecode('00:01:19', video_fps)

        video.set_duration(start_time=start_time, end_time=end_time)
        sm.auto_downscale = True

        video.start()
        sm.detect_scenes(video)
        scene_list = sm.get_scene_list()
        assert len(scene_list) == len(start_frames)
        detected_start_frames = [
            timecode.get_frames() for timecode, _ in scene_list ]
        assert all(x == y for (x, y) in zip(start_frames, detected_start_frames))



def test_adaptive_detector(test_movie_clip):
    """ Test SceneManager with VideoStreamCv2 and AdaptiveDetector. """
    # We use the ground truth of ContentDetector with threshold=27.
    start_frames = TEST_MOVIE_CLIP_GROUND_TRUTH_CONTENT[1][1]
    video = VideoStreamCv2(test_movie_clip)
    sm = SceneManager()
    assert sm._stats_manager is None
    # The SceneManager should implicitly create a StatsManager since this
    # detector requires it.
    sm.add_detector(AdaptiveDetector(video))
    assert sm._stats_manager is not None

    video_fps = video.frame_rate
    start_time = FrameTimecode('00:00:50', video_fps)
    end_time = FrameTimecode('00:01:19', video_fps)

    video.set_duration(start_time=start_time, end_time=end_time)
    sm.auto_downscale = True

    video.start()
    sm.detect_scenes(video)
    scene_list = sm.get_scene_list()
    assert len(scene_list) == len(start_frames)
    detected_start_frames = [
        timecode.get_frames() for timecode, _ in scene_list ]
    assert all(x == y for (x, y) in zip(start_frames, detected_start_frames))



# Defaults for now.
TEST_VIDEO_FILE_GROUND_TRUTH_THRESHOLD = [
    0, 15, 198, 376
]

def test_threshold_detector(test_video_file):
    """ Test SceneManager with VideoStreamCv2 and ThresholdDetector. """
    video = VideoStreamCv2(test_video_file)
    sm = SceneManager()
    sm.add_detector(ThresholdDetector())

    sm.auto_downscale = True

    video.start()
    sm.detect_scenes(video)
    scene_list = sm.get_scene_list()
    assert len(scene_list) == len(TEST_VIDEO_FILE_GROUND_TRUTH_THRESHOLD)
    detected_start_frames = [
        timecode.get_frames() for timecode, _ in scene_list ]
    assert all(x == y for (x, y) in zip(
        TEST_VIDEO_FILE_GROUND_TRUTH_THRESHOLD, detected_start_frames))



def test_detectors_with_stats(test_video_file):
    """ Test all detectors functionality with a StatsManager. """
    for detector in [ContentDetector, ThresholdDetector, AdaptiveDetector]:
        video = VideoStreamCv2(test_video_file)
        stats = StatsManager()
        sm = SceneManager(stats_manager=stats)
        sm.add_detector(create_detector(detector, video))

        end_time = FrameTimecode('00:00:15', video.frame_rate)

        video.set_duration(end_time=end_time)
        sm.auto_downscale = True

        video.start()
        sm.detect_scenes(video)
        initial_scene_len = len(sm.get_scene_list())
        assert initial_scene_len > 0   # test case must have at least one scene!
        # Re-analyze using existing stats manager.
        sm = SceneManager(stats_manager=stats)
        sm.add_detector(create_detector(detector, video))

        video.release()
        video.reset()
        video.set_duration(end_time=end_time)
        sm.auto_downscale = True
        video.start()

        sm.detect_scenes(video)
        scene_list = sm.get_scene_list()
        assert len(scene_list) == initial_scene_len

