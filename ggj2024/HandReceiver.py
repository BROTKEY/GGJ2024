import socket
import threading


class Hand:
    x = 0
    y = 0
    z = 0

    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return "x: {}\t\ty: {}\t\tz: {}".format(self.x, self.y, self.z)


class HandReceiver:
    left_hand: Hand = Hand(0, 0, 0)
    right_hand: Hand = Hand(0, 0, 0)
    run = True

    def __init__(self, addr="127.0.0.1", port=42069):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((addr, port))
        self.recv_thread = threading.Thread(target=self.data_receiver)
        self.recv_thread.start()

    def data_receiver(self):
        while self.run:
            data = self.sock.recv(1024)

            if not data:
                break

            self.sock.send(b"OK")

            data = str(data, "utf-8")
            left_hand, right_hand = data.split("|")

            self.left_hand = Hand(*left_hand.split(";"))
            self.right_hand = Hand(*right_hand.split(";"))

    def stop(self):
        self.run = False


if __name__ == "__main__":
    hands = HandReceiver()
    while True:
        print(f"Left Hand:\t {hands.left_hand}")
        print(f"Right Hand:\t {hands.right_hand}")
