# Priority Queue using list


class Priority_Queue:
  def __init__(self):
    self.queue=[]
    
  def is_empty(self):
    return len(self.queue)==0
    
  def push(self,data):
    if self.is_empty():
      self.queue.append(data)
    else:
      flag=False
      for i in range(0,len(self.queue)):
        if self.queue[i][1]>data[1]:
          flag=True
          self.queue.insert(i,data)
          break
      else:
        self.queue.append(data)
  
  def pop(self):
    if self.is_empty():
      return None
    
    return self.queue.pop()
    
  def top_element(self):
    if self.is_empty():
      return None
    return self.queue[len(self.queue)-1]
    
    
    
pq = Priority_Queue()

pq.push((3,4))
pq.push((2,1))
pq.push((1,2))
print('top element:',pq.top_element())
print(pq.pop())
print('top element:',pq.top_element())
print(pq.pop())
print(pq.pop())