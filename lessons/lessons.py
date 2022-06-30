import os
import threading
from threading import Thread
import sys
import imp

class thread_stoppable(threading.Thread):
  def __init__(self, *args, **keywords):
    threading.Thread.__init__(self, *args, **keywords)
    self.killed = False

  def start(self):
    self.__run_backup = self.run
    self.run = self.__run
    threading.Thread.start(self)

  def __run(self):
    sys.settrace(self.globaltrace)
    self.__run_backup()
    self.run = self.__run_backup

  def globaltrace(self, frame, event, arg):
    if event == 'call':
      return self.localtrace
    else:
      return None

  def localtrace(self, frame, event, arg):
    if self.killed:
      if event == 'line':
        raise SystemExit()
    return self.localtrace

  def kill(self):
    self.killed = True
    

dirname = os.path.dirname(__file__)
           
def get_full(num:int):
    global dirname
    with open(dirname + '/{}/text.txt'.format(num), encoding='utf-8') as file:
        full = file.readlines()
    
    i = 0
    while i < len(full) - 1:
        if (full[i] == '\n') and (full[i+1] == '\n'):
            del full[i]
        else:
            i+=1
            
    photos = os.listdir(dirname + '/{}/photos/'.format(num)) 

    i = 0
    while i < len(full) - 1:
        if not ('<#&'  in full[i+1]):
            full[i] += full[i+1]
            del full[i+1]
            
        else:
            number = int(full[i+1][3:].split('>')[0])
            full[i+1] = dirname+'/{}/photos/'.format(num)+photos[number-1]
            i += 2

    i = len(full)-1
    while full[i] == '\n':
        del full[i]
        i -= 1

    return full 
              

        
def get_test(num:int):
    global dirname
    with open(dirname + '/{}/test.txt'.format(num), encoding='utf-8') as file:
        full = file.readlines()

    i =  0
    while i < len(full) - 1:
        if full[i] == '\n':
            del full[i]
        else:
            full[i] = full[i][:-1]
            i += 1
    
    slovar = {full[i]:[full[i + 1],
                       full[i + 2],
                       full[i + 3],
                       full[i + 4],] for i in range(0, len(full), 5)}
    return slovar


def get_programming(num:int):
    
    with open(dirname + '/{}/programming.txt'.format(num), encoding='utf-8') as file:
        full = file.readlines()[:1]
    
    return full[0]





def checking(your_id, last_lesson):
    global dirname
    with open(dirname + '/programs/prog.py', encoding='utf-8') as file:
        full = file.readlines()
    
    for i in range(len(full)):
        full[i] = '\t' + full[i]

    full.append(full[-1])

    for i in list(range(len(full)-1))[::-1]:
        full[i+1] = full[i]

    full[0] = 'def main():\n'
    full.append('\n')
    full.append('''if __name__ == '__main__':\n''')
    full.append('\tmain()')

    f = open(dirname + '/programs/prog.py', 'r+', encoding='utf-8',)

    answer = ''
    for i in full:
        answer += i
     
    f.write(answer)
    f.close()
    
    if 'import' in answer:
        return 'Ошибка. Вы не можете импортировать библиотеки.'
    print(last_lesson)
    with open(dirname + '/{}/programming.txt'.format(last_lesson), encoding='utf-8') as file:
        full = file.readlines()[1:]
    
    for i in range(len(full)):
        full[i] = full[i][:-1]
    print(*full)
    try:
    
    
        import programs.prog as app
        imp.reload(app)
    except:
         return 'Ошибка компиляции'
    
    def test_app(full):
        input_values = [i for i in map(str, full[0].split())]
        
        output = []
    
        def mock_input():
            return input_values.pop(0)
        app.input = mock_input
        app.print = lambda x : output.append(x)
    
        app.main()
    
        return output
    output = [i for i in map(int, full[1].split())]

    try:
        print(output)
        print(test_app(full))
        return test_app(full) == output

    except:
        return 'Ошибка компиляции'
    



