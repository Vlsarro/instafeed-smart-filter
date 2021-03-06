import os
import json
import pathlib
import config

from cat_classifier import CatPipeline
from exc import JSONFileInvalidFormatException, JSONFileLoadingException
from util import get_exc_data, save_file_from_url


__all__ = ('FeedItem', 'process_feed_data', 'load_instagram_user_data')


def get_user_media_path(user_id):
    return os.path.join(config.SAVED_DATA_PATH, user_id)


class FeedItem:

    user = None
    is_video = None
    link = None
    id = None
    images = None

    is_media_saved = False
    user_media_path = None

    def __init__(self, raw_item: dict):
        self.raw_data = self._extract(raw_item)
        self.__dict__.update(self.raw_data)
        self.user_id = self.raw_data['user']['id']
        self.username = self.raw_data['user']['username']
        self.thumbnail_link = self.link + 'media'

    @staticmethod
    def _extract(raw_item: dict) -> dict:
        return raw_item['node']

    def save_media(self):
        if self.is_video:
            self.is_media_saved = self._save_video()
        else:
            self.is_media_saved = self._save_img()

    def _save_img(self) -> bool:
        result = False
        try:
            img_url = self.images['standard_resolution']['url']
        except KeyError:
            print(f'Save media error: {get_exc_data()}')
        else:
            try:
                self.user_media_path = get_user_media_path(self.user['id'])
                pathlib.Path(self.user_media_path).mkdir(exist_ok=True, parents=True)
                file_path = pathlib.Path(os.path.join(self.user_media_path, self.id))
                if not (file_path.exists() and file_path.is_file()):
                    try:
                        file_path.touch()
                    except FileExistsError:
                        print(f'File {file_path.resolve()} already exists, skip saving')
                        result = True
                    else:
                        save_file_from_url(img_url, file_path.resolve())
                        result = True
                else:
                    result = True
            except Exception:
                print(f'Save media error: {get_exc_data()}')
        return result

    def _save_video(self) -> bool:
        # TODO: implement video saving
        raise NotImplementedError()

    def __str__(self):
        return f'{self.id}|{self.link}|{self.user["username"]}'


# Cat classifier

cat_classifier = CatPipeline()


def process_feed_data(user_id: int, feed_data: list) -> list:
    processed_data = []
    for item in feed_data:
        feed_item = FeedItem(item)
        try:
            feed_item.save_media()
        except NotImplementedError:
            print(get_exc_data())
        else:
            processed_data.append(feed_item)

    classification_result = cat_classifier.run(get_user_media_path(str(user_id)))

    processed_data_with_cats = []
    for item in processed_data:
        try:
            is_cat = classification_result[item.id]
        except KeyError:
            print(f'Classification mismatch, id: {item.id}')
        else:
            if is_cat:
                processed_data_with_cats.append(item)

    return processed_data_with_cats


def load_instagram_user_data(filepath: str) -> int:
    """
    The input is expected to be a JSON file of the following format:
    {"instagramUserId": 1233434543534}

    :param filepath: JSON file path
    :return: id of Instagram user
    """
    try:
        with open(filepath) as f:
            data = json.load(f)
            return data['instagramUserId']
    except KeyError as e:
        raise JSONFileInvalidFormatException(f'Invalid key: {str(e)}')
    except (ValueError, FileNotFoundError) as e:
        raise JSONFileLoadingException(str(e))
    except Exception:
        raise
