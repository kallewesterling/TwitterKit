# TwitterKit

TwitterKit is the package I have built to have full control over the data that `Tweepy` is helping me take in through their API.

If you want to set up a single tw

## How it works: Single tweet

Here's how to quickly set up a datapoint for a single tweet:

```python
t = TwitterKit.Tweet(1161653450641420288)
```

Each `Tweet` object has a `data` property, which is a dictionary containing all the data for the `Tweet`, accessible as:

```python
t.data
```

All of the `data` property's key-value pairs can be access through shortcuts such as:

```python
t.full_text
```

Each Tweet object also comes with a slicer, which provides you slices of the tweet's `full_text` element:

```python
t = TwitterKit.Tweet(1161653450641420288)
t[0:200]
```

Each `Tweet` object has a `Tweet.user` property that should be a `User` object (see below) if everything is correct:
```python
t.user.verified
```

Each Tweet and User object also has a secret `t._meta` property which can provide you with meta information about the cache file:

```python
t = TwitterKit.Tweet(1161653450641420288)
t._meta
```

## How it works: Multiple tweets

If you have a number of IDs that you'd like to combine into one larger dataset, that's completely doable with the help of `TwitterSet`:

```python
s = TwitterKit.TweetSet([1161653450641420288, 1189928616022478848, 1189683627342348288])
```

The `TweetSet` object works really nicely with the [TAGS package](https://github.com/kallewesterling/process-tags/tree/master), which can generate this type of list of tweet IDs for you:

```python
tags = TAGS.DocumentSet(directories=['../../datasets/folder-with-tsv-documents-from-tags/', '../../datasets/another-dataset-folder/'])
s = TwitterKit.TweetSet(tags.ids)
```

The `TwitterSet` object comes with a `pandas DataFrame` as well:

```python
s.df
```

You can slice a `TweetSet` and get a subset of the tweets inside it:

```python
s[0]
```

## Changing standard settings

The most important settings are provided as constants, and can be changed easily:

```python
TwitterKit.SUPPRESS_WARNINGS = True
TwitterKit.PROGRESSBAR = False
TwitterKit.TWEET_CACHE_DIR = "./twitter_cache/tweets/"
TwitterKit.TWEET_CACHE_DIR = "./twitter_cache/users/"
```

The settings should pretty self-explanatory.
