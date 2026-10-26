import lldb
count=0
def stop(frame,bp,dict):
 global count
 count+=1
 th=frame.GetThread()
 print('THROW',count,'TYPE',frame.FindRegister('x1').GetValue())
 for i in range(min(9,th.GetNumFrames())):print(th.GetFrameAtIndex(i))
 return False
