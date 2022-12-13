import ure
import machine

from at_cmd import ATCommandBase

class SIM7080G(ATCommandBase):

  def __init__(self, uart):
    super().__init__(uart)
    self._http_req_body_len = 2048
    self._http_req_header_len = 350
    self._recv_block_size = 1024
    self.__SIM7080G_HTTP_METHOD = {
      "GET": 1,
      "PUT": 2,
      "POST": 3,
      "PATCH": 4,
      "HEAD": 5
    }
  
  def isOK(self, buf):
    m = ure.search("\r\nOK\r\n", buf)
    return m is not None
  
  def activate(self, num):
    res = super().send_at_command("AT+CNACT=" + str(num) + ",1").decode()
    m = ure.search("\+APP PDP: " + str(num) + ",(\w+)", res)
    if m is None:
      print("Failed to extract activation result.")
      return False
    
    return m.group(1) == "ACTIVE"
  
  def deactivate(self, num):
    res = super().send_at_command("AT+CNACT=" + str(num) + ",0").decode()
    m = ure.search("\+APP PDP: " + str(num) + ",(\w+)", res)
    if m is None:
      print("Failed to extract activation result.")
      return False
    
    return m.group(1) == "DEACTIVE"
  
  def isNetworkActivated(self, num):
    res = super().send_at_command("AT+CNACT?").decode()
    m = ure.search("\+CNACT: " + str(num) + ",(\d+),\"([^\"]*)\"", res)
    if m is None:
      print("Failed to extract activation status")
      return False
    
    return m.group(1) == '1'

  def setAPN(self, apn, username, password):
    res = super().send_at_command("AT+CGDCONT=1,\"IP\",\"" + apn + "\"").decode()
    if not self.isOK(res):
      print("Failed to set APN name.")
      return False
  
    res = super().send_at_command("AT+CNCFG=0,1,\"" + apn + "\",\"" + username + "\",\"" + password + "\",3").decode()
    if not self.isOK(res):
      print("Failed to set APN user and pass.")
      return False
    
    return True
  
  def http_request(self, method, url, path, headers = None, body = None, params = None):
    return_object = {
      "success": False,
      "message": "",
      "status_code": 0,
      "response": b''
    }

    super().send_at_command("AT+SHCONF=\"URL\",\"" + url + "\"")
    super().send_at_command("AT+SHCONF=\"BODYLEN\"," + str(self._http_req_body_len))
    super().send_at_command("AT+SHCONF=\"HEADERLEN\"," + str(self._http_req_header_len))
    
    super().send_at_command("AT+SHCONN")
    conn_status = super().send_at_command("AT+SHSTATE?")
    if "+SHSTATE: 1" not in conn_status:
      print("Failed to connect host.")
      return_object["message"] = "Failed to connect host."
      return return_object
    
    super().send_at_command("AT+SHCHEAD")
    if headers is not None:
      for header_key, header_value in headers.items():
        super().send_at_command("AT+SHAHEAD=\"" + str(header_key) + "\",\"" + str(header_value) + "\"")
    
    super().send_at_command("AT+SHCPARA")
    if params is not None:
      for param_key, param_value in params.items():
        super().send_at_command("AT+SHCPARA=\"" + str(param_key) + "\",\"" + str(param_value))
    
    if body is not None:
      super().send_at_command("AT+SHBOD=" + str(len(body)) + ",10000", expect_response = ">")
      super().send_at_command(bytes(body, "utf-8"))
    
    request_method_number = self.__SIM7080G_HTTP_METHOD[method.upper()]
    request_result = super().send_at_command("AT+SHREQ=\"" + str(path) + "\"," + str(request_method_number), expect_response = "+SHREQ:", timeout = 10000).decode()

    m = ure.search("\+SHREQ: \"(\w+)\",(\d+),(\d+)", request_result)
    if (m is None):
      print("Failed to request: returned unexpected format.")
      return_object["message"] = "Failed to send request."
      return return_object
    
    response_status_code = int(m.group(2))
    response_size = int(m.group(3))
    
    response_body = b''
    for i in range(0, response_size, self._recv_block_size):
      startaddr = i
      datalen = self._recv_block_size if (i + self._recv_block_size < response_size) else (response_size - i)
      cmd = "AT+SHREAD=" + str(startaddr) + "," + str(datalen)
      buf = super().send_at_command(cmd, expect_response = None, timeout = 125, return_early = False)
      
      response_keyword = b"+SHREAD: " + bytes(str(datalen), "utf-8") + b"\r\n"
      stringed_index = buf.find(response_keyword)
      response_body = b''.join([response_body, buf[(stringed_index + len(response_keyword)):-2]])
    
    super().send_at_command("AT+SHDISC")
    
    return_object["success"] = True
    return_object["status_code"] = response_status_code
    return_object["response"] = response_body
    return return_object
