import machine
import utime

class ATCommandBase:
  def __init__(self, uart):
    self.__uart = uart
  
  def send_at_command(self, command, expect_response = "OK", timeout = 1000, return_early = True):
    self.__uart.write(command)
    self.__uart.write(b"\r\n")
    
    recv_buf = b''
    start_time = utime.ticks_ms()
    while True:
      period = utime.ticks_diff(utime.ticks_ms(), start_time)
      if (period > timeout):
        break
      
      if self.__uart.any():
        read = self.__uart.read()
        recv_buf = b''.join([recv_buf, read])
        
      if ((recv_buf != b'') and return_early):
        if expect_response in recv_buf.decode():
          break
    
    return recv_buf
  