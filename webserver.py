import network
import machine
import usocket
TITLE = "RedSpoof"
def ok(socket, query):
    import config
    socket.write("HTTP/1.1 200 OK\r\n\r\n")
    socket.write("<!DOCTYPE html><title>"+TITLE+"</title><body>")
    socket.write(TITLE+" status: ")
    socket.write("<h1>RedSpoof Config Page</h1>")
    socket.write("<br>")
    socket.write("<form method='POST' enctype='text/plain' action='/set'>"+
                     "<input type='text' size='48' name='track0' value='"+config.tracks[0]+"'><br>"+
                     "<input type='text' size='48' name='track1' value='"+config.tracks[1]+"'><br>"+                     
                     "<input type='submit' name='submit' value='Save'>"+
                     "</form>")

def err(socket, code, message):
    socket.write("HTTP/1.1 "+code+" "+message+"\r\n\r\n")
    socket.write("<h1>"+message+"</h1>")

def handle(socket):
    (method, url, version) = socket.readline().split(b" ")
    print(method)
    print(url)
    print(version)
    if b"?" in url:
        (path, query) = url.split(b"?", 2)
    else:
        (path, query) = (url, b"")
    while True:
        header = socket.readline()
#        print(header)
        if header == b"":
            return
        if header == b"\r\n":
            break

    if version != b"HTTP/1.0\r\n" and version != b"HTTP/1.1\r\n":
        err(socket, "505", "HTTP Version Not Supported")
    elif method == b"GET":
        if path == b"/":
            ok(socket, query)
        else:
            err(socket, "404", "Not Found")
    elif method == b"POST":
        #print(path)
       if path == b"/set":
        track0 = ""
        track1 = ""
        while True:
         postreq = socket.readline()
         print(postreq)
         if postreq == b"":
            return
         if postreq == b"\r\n":
            break
         if postreq[:7] == b"track0=":
            track0 = postreq[7:len(postreq)-2].decode()
         if postreq[:7] == b"track1=":
            track1 = postreq[7:len(postreq)-2].decode()
         if postreq == b"submit=Save\r\n":
            import config
            config.tracks[0] = track0
            config.tracks[1] = track1
            saveconfig(config)
            ok(socket,query)
            return "ok"
        ok(socket,query)

    else:
        err(socket, "501", "Not Implemented")

def saveconfig(newconfig):
   f = open('config.py', 'w')
   f.write('tracks = '+str(newconfig.tracks))
   f.close()
def main():
 server = usocket.socket()
 server.bind(('0.0.0.0', 80))
 server.listen(1)
 while True:
    try:
        (socket, sockaddr) = server.accept()
        if handle(socket) == "ok":
          socket.write("<!DOCTYPE html><title>"+TITLE+"</title><body>")
          socket.write("<h1>RedSpoof config accepted, resetting...</h1>")
          socket.write("</body></html>\r\n\r\n")
          socket.close()
          server.close()
          break
    except:
        socket.write("HTTP/1.1 500 Internal Server Error\r\n\r\n")
        socket.write("<h1>Internal Server Error</h1>")
    socket.close()

 machine.reset()
