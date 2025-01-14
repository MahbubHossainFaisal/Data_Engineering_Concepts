from pyspark.sql import SparkSession, Row
from pyspark.sql import functions as func

spark = SparkSession.builder().appName("friendsByAge").getOrCreate()

lines = spark.read.option("header","true").option("inferSchema","true").csv("file:///fakeFriends.csv")


people = lines.select(lines.age,lines.friends)

avg_friends = people.groupBy("age").avg("freinds").show()

avg_friends_sorted = people.groupBy("age").avg("friends").sort("age").show()

avg_friends_formatted = people.groupBy("age").agg(func.round(func.avg("friends"),2)).sort("age").show()

avg_friends_aliased_and_formatted = people.groupBy("age").agg(func.round(func.avg("friends"),2).alias("avg_friends")).sort("age").show()

spark.stop()