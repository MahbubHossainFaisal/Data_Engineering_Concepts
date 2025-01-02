from pyspark import SparkConf, SparkContext
import collection
conf = SparkConf().setMaster("local").setAppName("AverageAgeFriends")
sc = SparkContext(conf = conf)


def parseLine(line):
    fields = line.split(',')
    age = int(fields[2])
    numFriends = int(fields[3])

    return (age,numFriends)


lines = sc.textFile("file:///C:/Users/Mahbub/Desktop/Data Engineering/Spark/fakeFriends.csv")

rdd = lines.map(parseLine)

totalsByAge = rdd.mapValue(lambda x:(x,1)).reduceByKey(lambda x,y:x[0]+y[0],x[1]+y[1])

averagesByAge = totalsByAge.mapValue(lambda x:x[0]/x[1])

results = averagesByAge.collection()

for result in results:
    print(result)