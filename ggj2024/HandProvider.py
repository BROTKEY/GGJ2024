import leap
import socket
import threading
import mediapipe as mp
import cv2

class Provider:
    running = False

    def __init__(self, source, addr="127.0.0.1", port=42069):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((addr, port))
        self.sock.listen(4)
        self.connection_handler = threading.Thread(target=self.connection_handler)
        self.data = source

        print("Opened Socket on: {}:{}".format(addr, port))

    def connection_handler(self):
        while self.running:
            client, addr = self.sock.accept()

            print("Client {} connected!".format(addr))
            client_thread = threading.Thread(target=self.client_handler, args=(client, addr))
            client_thread.run()

    def client_handler(self, client, addr):
        while True:
            data = "{};{};{}|{};{};{}".format(*self.data.left_hand_position, *self.data.right_hand_position)

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
            else:
                self.right_hand_position = (hand.palm.position.x, hand.palm.position.y, hand.palm.position.z)


class MediapipeListener:
    left_hand_position = (0, 0, 0)
    right_hand_position = (0, 0, 0)
    running = True

    def __init__(self, capture_device=0, x_scale=1, y_scale=1, model_complexity=0, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self.capture = cv2.VideoCapture(capture_device)
        self.hands = mp.solutions.hands.Hands(
                model_complexity=model_complexity,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence
            )
        self.mediapipe_thread = threading.Thread(target=self.loop)
        self.mediapipe_thread.start()

    def loop(self):
        while self.running:
            success, image = self.capture.read()
            if not success:
                print("Ignoring empty camera frame.")
                continue

            image = cv2.flip(image, 1)
            image.flags.writeable = False # Apparently improves performance
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self.hands.process(image)

            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            if results.multi_hand_landmarks:
                handedness = results.multi_handedness
                for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    if handedness[i].label == "Left":
                        print("Left")
                    mp.solutions.drawing_utils.draw_landmarks(
                                image,
                                hand_landmarks,
                                mp.solutions.hands.HAND_CONNECTIONS,
                                mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                                mp.solutions.drawing_styles.get_default_hand_connections_style()
                            )
            cv2.imshow("THOSE ARE YOUR HANDS", image)
            if cv2.waitKey(5) & 0xFF == 27:
                break

    def __del__(self):
        self.running = False
        self.capture.release()



if __name__ == "__main__":
    #listener = LeapListener()

    #connection = leap.Connection()
    #connection.add_listener(listener)

    #with connection.open():
    #    connection.set_tracking_mode(leap.TrackingMode.Desktop)
    listener = MediapipeListener()

    provider = Provider(listener)
    provider.start()

    input("Press Enter to Exit")

    provider.stop()
    exit(0)
