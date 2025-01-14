from pyspark.sql import SparkSession, Row
import collections


spark = SparkSession.builder.appName("teenagers").getOrCreate()



def mapper(line):
    data = line.split(',')
    id = int(data[0])
    name = str(data[1].encode('utf-8'))
    age = int(data[2])
    numFriends = int(data[3])

    return Row(id,name,age,numFriends)
    

lines = spark.SparkContext.textFile("fakeFriends.csv")

people = lines.map(mapper)

peopleSchema = people.createDataframe('people').cache()
peopleSchema.createOrReplaceTempView()

teenagers = spark.sql("select * from people where age> 10 and age < 21");

for teen in teenagers.collect():
    print(teen)


peopleSchema.groupBy("age").count().orderBy("age").show()


spark.stop()