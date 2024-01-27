import leap
import socket
import threading


class LeapProvider:
    running = False

    def __init__(self, leaplistener: "LeapListener", addr="127.0.0.1", port=42069):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((addr, port))
        self.sock.listen(4)
        self.connection_handler = threading.Thread(target=self.connection_handler)
        self.leap = leaplistener

        print("Opened Socket on: {}:{}".format(addr, port))

    def connection_handler(self):
        while self.running:
            client, addr = self.sock.accept()

            print("Client {} connected!".format(addr))
            client_thread = threading.Thread(target=self.client_handler, args=(client, addr))
            client_thread.run()

    def client_handler(self, client, addr):
        while True:
            data = "{};{};{}|{};{};{}|{}|{}".format(*self.leap.left_hand_position, *self.leap.right_hand_position, self.leap.left_hand_grab_angle, self.leap.right_hand_grab_angle)

            try:
                client.send(bytes(data, 'utf-8'))
                data = client.recv(1024)
            except ConnectionResetError:
                break

            if not data:
                break

        print("Client {} disconnected!".format(addr))
        client.close()

    def start(self):
        self.running = True
        self.connection_handler.start()

    def stop(self):
        self.running = False
        self.sock.close()

    def __del__(self):
        self.stop()


class LeapListener(leap.Listener):
    left_hand_position = (0, 0, 0)
    right_hand_position = (0, 0, 0)

    left_hand_grab_angle = 0
    right_hand_grab_angle = 0

    def on_connection_event(self, event):
        print("Connected")

    def on_device_event(self, event):
        try:
            with event.device.open():
                info = event.device.get_info()
        except leap.LeapCannotOpenDeviceError:
            info = event.devide.get_info()

        print("Found device {}".format(info))

    def on_tracking_event(self, event):
        for hand in event.hands:
            if str(hand.type) == "HandType.Left":
                self.left_hand_position = (hand.palm.position.x, hand.palm.position.y, hand.palm.position.z)
                self.left_hand_grab_angle = hand.grab_angle
            else:
                self.right_hand_position = (hand.palm.position.x, hand.palm.position.y, hand.palm.position.z)
                self.right_hand_grab_angle = hand.grab_angle


if __name__ == "__main__":
    listener = LeapListener()

    connection = leap.Connection()
    connection.add_listener(listener)

    with connection.open():
        connection.set_tracking_mode(leap.TrackingMode.Desktop)
        provider = LeapProvider(listener)
        provider.start()

        input("Press Enter to Exit")

        provider.stop()
        exit(0)
