import json, yaml, re
from pathlib import Path
import progressbar as pb


# Set up cache directories
tweet_cache_dir = Path('/Users/kallewesterling/_twitter_cache/tweets/')
user_cache_dir = Path('/Users/kallewesterling/_twitter_cache/users/')

if not tweet_cache_dir.is_dir(): tweet_cache_dir.mkdir(parents=True)
if not user_cache_dir.is_dir(): user_cache_dir.mkdir(parents=True)



class Tweet():
    def __init__(self, id_str, suppress_warnings=False):
        self.cache_dir = tweet_cache_dir
        self.suppress_warnings = suppress_warnings
        
        self.id_str = str(id_str)
        self._json = get_json_from_cache(self.id_str, self.cache_dir)
        
        self.error_handle()
        
        self.created_at = self._json.get('created_at', None)
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

        if isinstance(self.user, dict): self.user = self.user['id_str']
        self.user = User(self.user)

        self.retweet = self.is_retweet()


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

class User():
    def __init__(self, id_str):
        self.cache_dir = user_cache_dir

        self.id_str = str(id_str)
        self._json = get_json_from_cache(self.id_str, self.cache_dir)

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


class TweetSet():
    def __init__(self, ids=[], suppress_warnings=False, progressbar=True, filter_key=None, filter_value=None, include_retweets=True):
        self.suppress_warnings = suppress_warnings
        self.ids = ids
        self.progressbar = progressbar
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

    def __repr__(self):
        return(f"TweetSet consisting of {len(self.tweets)} tweets.")

    def __len__(self):
      return(len(self.tweets))


def get_json_from_cache(id_str, cache_dir):
    tweet_cache = cache_dir / id_str
    if not tweet_cache.is_file():
        raise RuntimeError(f"File {id} could not be opened.")
    else:
        with open(tweet_cache, "r") as f:
            _json = json.load(f)
        return(_json)


def _expand_contractions(text, c_re=None):
    with open("./configuration/contractions.yml") as f:
        contractions = yaml.load(stream=f)
    if c_re is None: c_re = re.compile('(%s)' % '|'.join(contractions.keys()))
    def replace(match):
        return contractions[match.group(0)]
    return(c_re.sub(replace, text))


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