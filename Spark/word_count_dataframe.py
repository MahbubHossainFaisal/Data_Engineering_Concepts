from pyspark.sql import SparkSession
from pyspark.sql import functions as func

spark = SparkSession.builder.appName("WordCount").getOrCreate()


inputDF = spark.read.text("file:///C:/Users/Mahbub/Desktop/Data Engineering/Spark/book.txt")


words = inputDF.select(func.explode(func.split(inputDF.value,"\\W+")).alias("word"))

wordsWithoutEmptyString = words.filter(words.word != "")

smallerCaseWords =  words.select(func.lower(wordsWithoutEmptyString.word).alias("word"))

wordCount = smallerCaseWords.groupBy("word").count()

wordCountSorted = wordCount.sort("count")

wordCountSorted.show(wordCountSorted.count())