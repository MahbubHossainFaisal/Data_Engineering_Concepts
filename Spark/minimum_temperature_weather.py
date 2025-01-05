from spark import SparkConf, SparkContext
import collections

conf = SparkConf().setMaster("local").setAppName("min_weather_temperature")
sc = SparkContext(conf = conf)


def parseLine(line):
    id = line[0]
    entry = line[2]
    temp = float(line[3]) * 0.1 * (9/5) + 32
    return (id,entry,temp)

lines = sc.readText("file:///spark/weather1800.csv")

line = lines.map(parseLine)

weather_filter = lines.filter(lambda x: "TMIN" in x[1])

weather_temp = weather_filter.map(lambda x: (x[0],x[2]))

min_temp = weather_temp.reduceByKey(lambda x,y: min(x,y))

results = min_temp.collect()

for result in results:
    print(f'{result[0]} -> {result[1]} farenhight')