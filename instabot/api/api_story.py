from __future__ import unicode_literals
import os
import shutil
import time
from random import randint
from requests_toolbelt import MultipartEncoder
import json

from . import config
from .api_photo import stories_shaper, get_image_size


def download_story(self, filename, story_url, username):
    path = "stories/{}".format(username)
    if not os.path.exists(path):
        os.makedirs(path)
    fname = os.path.join(path, filename)
    if os.path.exists(fname):  # already exists
        self.logger.info("Stories already downloaded...")
        return os.path.abspath(fname)
    response = self.session.get(story_url, stream=True)
    if response.status_code == 200:
        with open(fname, 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
        return os.path.abspath(fname)


def upload_story_photo(self, photo, upload_id=None):
    if upload_id is None:
        upload_id = str(int(time.time() * 1000))
    photo = stories_shaper(photo)
    if not photo:
        return False

    with open(photo, 'rb') as f:
        photo_bytes = f.read()

    data = {
        'upload_id': upload_id,
        '_uuid': self.uuid,
        '_csrftoken': self.token,
        'image_compression': '{"lib_name":"jt","lib_version":"1.3.0","quality":"87"}',
        'photo': ('pending_media_%s.jpg' % upload_id, photo_bytes, 'application/octet-stream', {'Content-Transfer-Encoding': 'binary'})
    }
    m = MultipartEncoder(data, boundary=self.uuid)
    self.session.headers.update({'X-IG-Capabilities': '3Q4=',
                                 'X-IG-Connection-Type': 'WIFI',
                                 'Cookie2': '$Version=1',
                                 'Accept-Language': 'en-US',
                                 'Accept-Encoding': 'gzip, deflate',
                                 'Content-type': m.content_type,
                                 'Connection': 'close',
                                 'User-Agent': self.user_agent})
    response = self.session.post(
        config.API_URL + "upload/photo/", data=m.to_string())

    if response.status_code == 200:
        upload_id = json.loads(response.text).get('upload_id')
        if self.configure_story_photo(upload_id, photo):
            return True
    return False


def configure_story_photo(self, upload_id, photo):
    (w, h) = get_image_size(photo)
    data = self.json_data({
        'source_type': 4,
        'upload_id': upload_id,
        'story_media_creation_date': str(int(time.time()) - randint(11, 20)),
        'client_shared_at': str(int(time.time()) - randint(3, 10)),
        'client_timestamp': str(int(time.time())),
        'configure_mode': 1,      # 1 - REEL_SHARE, 2 - DIRECT_STORY_SHARE
        'device': self.device_settings,
        'edits': {
            'crop_original_size': [w * 1.0, h * 1.0],
            'crop_center': [0.0, 0.0],
            'crop_zoom': 1.3333334
        },
        'extra': {
            'source_width': w,
            'source_height': h,
        }})
    return self.send_request('media/configure_to_story/?', data)

# TODO FIX, DOES NOT WORK
def upload_story_video(self, video, upload_id=None):
    if upload_id is None:
        upload_id = str(int(time.time() * 1000))
    video, thumbnail, width, height, duration = resize_video(video)
    data = {
        'upload_id': upload_id,
        '_csrftoken': self.token,
        'media_type': '2',
        '_uuid': self.uuid,
    }
    m = MultipartEncoder(data, boundary=self.uuid)
    self.session.headers.update({'X-IG-Capabilities': '3Q4=',
                                 'X-IG-Connection-Type': 'WIFI',
                                 'Host': 'i.instagram.com',
                                 'Cookie2': '$Version=1',
                                 'Accept-Language': 'en-US',
                                 'Accept-Encoding': 'gzip, deflate',
                                 'Content-type': m.content_type,
                                 'Connection': 'keep-alive',
                                 'User-Agent': self.user_agent})
    response = self.session.post(
        config.API_URL + "upload/video/", data=m.to_string())
    if response.status_code == 200:
        body = json.loads(response.text)
        upload_url = body['video_upload_urls'][3]['url']
        upload_job = body['video_upload_urls'][3]['job']

        with open(video, 'rb') as video_bytes:
            video_data = video_bytes.read()
        # solve issue #85 TypeError: slice indices must be integers or None or have an __index__ method
        request_size = len(video_data) // 4
        last_request_extra = len(video_data) - 3 * request_size

        headers = copy.deepcopy(self.session.headers)
        self.session.headers.update({
            'X-IG-Capabilities': '3Q4=',
            'X-IG-Connection-Type': 'WIFI',
            'Cookie2': '$Version=1',
            'Accept-Language': 'en-US',
            'Accept-Encoding': 'gzip, deflate',
            'Content-type': 'application/octet-stream',
            'Session-ID': upload_id,
            'Connection': 'keep-alive',
            'Content-Disposition': 'attachment; filename="video.mov"',
            'job': upload_job,
            'Host': 'upload.instagram.com',
            'User-Agent': self.user_agent
        })
        for i in range(4):
            start = i * request_size
            if i == 3:
                end = i * request_size + last_request_extra
            else:
                end = (i + 1) * request_size
            length = last_request_extra if i == 3 else request_size
            content_range = "bytes {start}-{end}/{len_video}".format(
                start=start, end=end - 1, len_video=len(video_data)).encode('utf-8')

            self.session.headers.update(
                {'Content-Length': str(end - start), 'Content-Range': content_range})
            response = self.session.post(
                upload_url, data=video_data[start:start + length])
        self.session.headers = headers

        if response.status_code == 200:
            # if self.configure_video(upload_id, video, thumbnail, width, height, duration):
            #     self.expose()
            #     from os import rename
            #     rename(video, "{}.REMOVE_ME".format(video))
            #     return True
            # upload_id = json.loads(response.text).get('upload_id')
            print(response.text)
            print("Video uploaded: upload_id={}, thumbnail={}".format(
                upload_id, thumbnail))
            if self.configure_story_video(upload_id, thumbnail, width, height, duration):
                return True
    return False


def configure_story_video(self, upload_id, thumbnail, width, height, duration):

        self.upload_photo(photo=thumbnail, upload_id=upload_id, from_video=True)

        data = self.json_data({
            'source_type': '4',
            'upload_id': upload_id,
            'story_media_creation_date': str(int(time.time()) - randint(11, 20)),
            'client_shared_at': str(int(time.time()) - randint(3, 10)),
            'client_timestamp': str(int(time.time())),
            'configure_mode': 1,      # 1 - REEL_SHARE, 2 - DIRECT_STORY_SHARE
            'poster_frame_index': 0,
            'length': duration * 1.0,
            'audio_muted': False,
            'filter_type': 0,
            'video_result': 'deprecated',
            'clips': {
                'length': duration * 1.0,
                'source_type': '4',
                'camera_position': 'back'
            },
            'device': self.device_settings,
            'extra': {
                'source_width': width,
                'source_height': height,
            }
        })
        
        return self.send_request('media/configure_to_story/?video=1', data)
