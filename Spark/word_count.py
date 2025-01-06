from pyspark import SparkConf, SparkContext
import re

# Configure Spark
conf = SparkConf().setMaster("local").setAppName("WordCount")
sc = SparkContext(conf=conf)

# Function to normalize words
def normalize_words(line):
    # Split line into words using regex for non-word characters
    return re.compile(r'\W+', re.UNICODE).split(line.lower())

# Load the text file
lines = sc.textFile("file:///spark/weather1800.csv")

# Normalize words
words = lines.flatMap(normalize_words)

# Count occurrences of each word
word_counts = words.map(lambda word: (word, 1)).reduceByKey(lambda x, y: x + y)

# Sort by counts (ascending order)
word_counts_sorted = word_counts.map(lambda pair: (pair[1], pair[0])).sortByKey()

# Collect results
results = word_counts_sorted.collect()

# Print results
for count, word in results:
    if word:  # Exclude empty words
        print(f"{word}:\t{count}")
