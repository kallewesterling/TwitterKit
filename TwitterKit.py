import json, yaml, re, time, tweepy
from pathlib import Path
from datetime import datetime
from itertools import islice
import progressbar as pb
import pandas as pd

from pprint import pprint # for dev purposes only


# Constants
SUPPRESS_WARNINGS = False
PROGRESSBAR = False
CREDENTIALS = './credentials.yml'




# Set up cache directories
TWEET_CACHE_DIR = Path('/Users/kallewesterling/_twitter_cache/tweets/')
USER_CACHE_DIR = Path('/Users/kallewesterling/_twitter_cache/users/')

if not TWEET_CACHE_DIR.is_dir(): TWEET_CACHE_DIR.mkdir(parents=True)
if not USER_CACHE_DIR.is_dir(): USER_CACHE_DIR.mkdir(parents=True)



def _load_cache(id_str, cache_dir):
    tweet_cache = cache_dir / id_str
    if tweet_cache.is_file():
        with open(tweet_cache, "r") as f:
            _json = json.load(f)
            _json['_cache_meta'] = {}
            _json['_cache_meta']['ctime'] = datetime.strftime(datetime.fromtimestamp(tweet_cache.stat().st_ctime), "%Y-%m-%d %H:%M:%S")
            _json['_cache_meta']['mtime'] = datetime.strftime(datetime.fromtimestamp(tweet_cache.stat().st_mtime), "%Y-%m-%d %H:%M:%S")
            _json['_cache_meta']['atime'] = datetime.strftime(datetime.fromtimestamp(tweet_cache.stat().st_atime), "%Y-%m-%d %H:%M:%S")
        return(_json)
    else:
        return(None)
        # raise RuntimeError(f"File {tweet_cache} could not be opened.")

def _dump_cache(id_str, cache_dir, _json):
    tweet_cache = cache_dir / id_str
    if not tweet_cache.is_file():
        with open(tweet_cache, "w+") as f:
            json.dump(_json, f)
        return(True)
    else:
        raise RuntimeError(f"Tweet {id_str} has already been downloaded: {tweet_cache}.")


class _API():
  def __init__(self, CREDENTIALS = CREDENTIALS):
    CREDENTIALS = Path(CREDENTIALS)
    if not CREDENTIALS.exists(): raise RuntimeError(f"Credentials file {CREDENTIALS} for Twitter API access does not exist.")
    with open(CREDENTIALS, 'r') as f:
      self.credentials = yaml.safe_load(f)
    auth = tweepy.OAuthHandler(self.credentials['CONSUMER_KEY'], self.credentials['CONSUMER_SECRET'])
    auth.set_access_token(self.credentials['ACCESS_TOKEN'], self.credentials['ACCESS_TOKEN_SECRET'])
    self.api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

_api_class = _API()
api = _api_class.api


class TweetSet():
    def __init__(self, ids=[], suppress_warnings=None, progressbar=None, filter_key=None, filter_value=None, include_retweets=True):

        if not suppress_warnings: self.suppress_warnings = SUPPRESS_WARNINGS
        else: self.suppress_warnings = suppress_warnings

        if not progressbar: self.progressbar = PROGRESSBAR
        else: self.progressbar = progressbar

        self.ids = ids
        self.tweets = []
        if filter_key is not None:
          self.filter_key = filter_key
        else:
          self.filter_key = None
        if filter_value is not None:
          self.filter_value = filter_value.lower()
        else:
          self.filter_value = None

        if self.progressbar: bar = pb.ProgressBar(maxval=len(self.ids)).start()

        for i, id in enumerate(ids):
            f = None

            if self.progressbar: bar.update(i)

            tweet = Tweet(id, suppress_warnings=self.suppress_warnings)

            if self.filter_key and self.filter_value:
              f = Filter(tweet, self.filter_key, self.filter_value)
              filter_out = f.filter_out
            else:
              filter_out = None

            if tweet.retweet and include_retweets and not filter_out:
              self.tweets.append(tweet) # we want retweets and this tweet has not been filtered so it's good to go
            elif tweet.retweet and include_retweets and filter_out:
              pass # we want retweets but this tweet has already been filtered
            elif not tweet.retweet and not filter_out:
              self.tweets.append(tweet) # this is an original tweet so we want to do this.
            elif not tweet.retweet and filter_out:
              pass # we want to capture it but it has been filtered out already
            elif tweet.retweet and not include_retweets:
              pass # we don't want retweets, no matter whether they've been filtered or not
            else:
              print("tweet.retweet: ", tweet.retweet, "\ninclude_retweets", include_retweets, "\nfilter_out", filter_out)
        if self.progressbar: bar.finish()

        _ = [t.data for t in self.tweets]
        self.df = pd.DataFrame.from_dict(_)


    def __len__(self):
      return(len(self.tweets))


    def __getitem__(self, loc):
      return(self.tweets[loc])


    def __repr__(self):
      return(f"TwitterKit.TweetSet({self.ids})")


class Filter():

  def __init__(self, tweet = None, filter_key = None, filter_value = None):
    self.tweet = tweet
    self.filter_key = filter_key
    self.filter_value = filter_value.lower()

    test_value = tweet._json.get(self.filter_key, "").lower()
    if self.filter_value in test_value:
      self.filter_in = True
      self.filter_out = False
    elif self.filter_value not in test_value:
      self.filter_in = False
      self.filter_out = True
    else:
      raise RuntimeError("Something strange happened here.")









class Tweet():
    def __init__(self, id_str, suppress_warnings=None):
        self.cache_dir = TWEET_CACHE_DIR

        if not suppress_warnings: self.suppress_warnings = SUPPRESS_WARNINGS
        else: self.suppress_warnings = suppress_warnings

        self.id_str = str(id_str)
        self._json = _load_cache(self.id_str, self.cache_dir)

        if self._json is None:
          self._download_live_data()
          self._json = _load_cache(self.id_str, self.cache_dir)

        self.error_handle()

        self.created_at = self._json.get('created_at', None)
        try:
          self.created_at_ts = time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(self.created_at,'%a %b %d %H:%M:%S +0000 %Y'))
        except:
          self.created_at_ts = None
        self.full_text = self._json.get('full_text', None)
        self.truncated = self._json.get('truncated', None)
        self.entities = self._json.get('entities', None)
        self.source = self._json.get('source', None)
        self.in_reply_to_status_id_str = self._json.get('in_reply_to_status_id_str', None)
        self.in_reply_to_user_id_str = self._json.get('in_reply_to_user_id_str', None)
        self.in_reply_to_screen_name = self._json.get('in_reply_to_screen_name', None)
        self.user = self._json.get('user', None)
        self.geo = self._json.get('geo', None)
        self.coordinates = self._json.get('coordinates', None)
        self.place = self._json.get('place', None)
        self.contributors = self._json.get('contributors', None)
        self.is_quote_status = self._json.get('is_quote_status', None)
        self.retweet_count = self._json.get('retweet_count', None)
        self.favorite_count = self._json.get('favorite_count', None)
        self.possibly_sensitive = self._json.get('possibly_sensitive', None)
        self.lang = self._json.get('lang', None)
        self.json_source = self._json.get('json_source', None)
        self._meta = self._json.get('_cache_meta', None)
        if isinstance(self.user, dict): self.user = self.user['id_str']
        self.user = User(self.user)

        self.retweet = self.is_retweet()

        self.data = {
          'id': int(self.id_str),
          'created_at': self.created_at,
          'created_at_ts': self.created_at_ts,
          'full_text': self.full_text,
          'truncated': self.truncated,
          'entities': self.entities,
          'source': self.source,
          'in_reply_to_status_id_str': self.in_reply_to_status_id_str,
          'in_reply_to_user_id_str': self.in_reply_to_user_id_str,
          'in_reply_to_screen_name': self.in_reply_to_screen_name,
          'user': self.user,
          'geo': self.geo,
          'coordinates': self.coordinates,
          'place': self.place,
          'contributors': self.contributors,
          'is_quote_status': self.is_quote_status,
          'retweet_count': self.retweet_count,
          'favorite_count': self.favorite_count,
          'possibly_sensitive': self.possibly_sensitive,
          'lang': self.lang,
          'json_source': self.json_source,
          'retweet': self.retweet,
          '_meta': self._meta
        }


    def is_retweet(self):
      return("retweeted_status" in self._json or self.full_text.lower()[0:2] == "rt")


    def error_handle(self):
        if 'error' in self._json:
            error = self._json['error'].replace("'",'"')
            try:
                error = json.loads(error)
                if not self.suppress_warnings: print(f"Warning: Error in tweet ID {self.id_str}. Message: {error[0]['message']} (Twitter error {error[0]['code']})")
            except ValueError:
                print(f"Tried to display error message! {error}")


    def _download_live_data(self):
      status = api.get_status(self.id_str, tweet_mode="extended")
      status._json['json_source'] = "Twitter"
      _dump_cache(self.id_str, self.cache_dir, status._json)


    def __repr__(self):
      return(f"TwitterKit.Tweet({self.id_str})")


    def __getitem__(self, key):
      if isinstance(key, int) and key >= 0:
          return "".join(list(islice(self.full_text, key, key + 1)))
      elif isinstance(key, slice):
          return "".join(list(islice(self.full_text, key.start, key.stop, key.step)))
      else:
          raise KeyError("Key must be non-negative integer or slice, not {}"
                          .format(key))

class User():
    def __init__(self, id_str):
        self.cache_dir = USER_CACHE_DIR

        self.id_str = str(id_str)
        self._json = _load_cache(self.id_str, self.cache_dir)

        if self._json is None:
          self._download_live_data()
          self._json = _load_cache(self.id_str, self.cache_dir)
      
        self.contributors_enabled = self._json.get('contributors_enabled', None)
        self.created_at = self._json.get('created_at', None)
        self.description = self._json.get('description', None)
        self.entities = self._json.get('entities', None)
        self.favourites_count = self._json.get('favourites_count', None)
        self.followers_count = self._json.get('followers_count', None)
        self.friends_count = self._json.get('friends_count', None)
        self.geo_enabled = self._json.get('geo_enabled', None)
        self.has_extended_profile = self._json.get('has_extended_profile', None)
        self.is_translation_enabled = self._json.get('is_translation_enabled', None)
        self.is_translator = self._json.get('is_translator', None)
        self.json_source = self._json.get('json_source', None)
        self.lang = self._json.get('lang', None)
        self.listed_count = self._json.get('listed_count', None)
        self.location = self._json.get('location', None)
        self.name = self._json.get('name', None)
        self.screen_name = self._json.get('screen_name', None)
        self.protected = self._json.get('protected', None)
        self.time_zone = self._json.get('time_zone', None)
        self.translator_type = self._json.get('translator_type', None)
        self.url = self._json.get('url', None)
        self.utc_offset = self._json.get('utc_offset', None)
        self.verified = self._json.get('verified', None)
        self.json_source = self._json.get('json_source', None)
        self._meta = self._json.get('_cache_meta', None)

        self.data = {
          'contributors_enabled': self.contributors_enabled,
          'created_at': self.created_at,
          'description': self.description,
          'entities': self.entities,
          'favourites_count': self.favourites_count,
          'followers_count': self.followers_count,
          'friends_count': self.friends_count,
          'geo_enabled': self.geo_enabled,
          'has_extended_profile': self.has_extended_profile,
          'is_translation_enabled': self.is_translation_enabled,
          'is_translator': self.is_translator,
          'json_source': self.json_source,
          'lang': self.lang,
          'listed_count': self.listed_count,
          'location': self.location,
          'name': self.name,
          'screen_name': self.screen_name,
          'protected': self.protected,
          'time_zone': self.time_zone,
          'translator_type': self.translator_type,
          'url': self.url,
          'utc_offset': self.utc_offset,
          'verified': self.verified,
          'json_source': self.json_source,
          '_meta': self._meta
        }

    def _download_live_data(self):
      status = api.get_user(id=self.id_str)
      print(self.id_str, self.cache_dir)
      pprint(status)
      status._json['json_source'] = "Twitter"
      _dump_cache(self.id_str, self.cache_dir, status._json)