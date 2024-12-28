#!/usr/bin/env python3
# camera_control_server.py

import os
import socket
import json
import threading

from camera_deplacement import CameraDeplacement  # <-- on importe notre classe

SOCKET_PATH = "/tmp/hailo_camera.sock"

class UserData:
    def __init__(self):
        self.barycentre_x = None
        self.barycentre_y = None

class CameraControlServer:
    def __init__(self, socket_path=SOCKET_PATH):
        self.socket_path = socket_path
        self.server_socket = None
        self._stop = False

        # Instanciation du contrôleur de caméra (PID + servos)
        self.camera_deplacement = CameraDeplacement(
            # Vous pouvez ajuster ici quelques paramètres par défaut
            p_horizontal=30.0,
            i_horizontal=0.01,
            d_horizontal=0.2,
            p_vertical=15.0,
            i_vertical=0.01,
            d_vertical=0.1,
            dead_zone=0.02  # zone morte à +/- 0.05 autour du centre
        )

        # Initialisation de user_data
        self.user_data = UserData()

    def start(self):
        # Si le fichier socket existe déjà, on le supprime
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(self.socket_path)
        self.server_socket.listen(1)
        print(f"[CameraControlServer] Serveur démarré sur {self.socket_path}")

        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop = True
        if self.server_socket:
            self.server_socket.close()
        if self.thread.is_alive():
            self.thread.join()
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        # Arrêt et remise à zéro des servos
        self.camera_deplacement.cleanup()

    def _accept_loop(self):
        while not self._stop:
            try:
                client_sock, addr = self.server_socket.accept()
                print("[CameraControlServer] Connexion entrante (Unix domain socket)")
                # On lance un thread qui va écouter ce client
                t = threading.Thread(
                    target=self._handle_client, 
                    args=(client_sock,),
                    daemon=True
                )
                t.start()
            except socket.error:
                if self._stop:
                    print("[CameraControlServer] Arrêt du serveur.")
                else:
                    raise

    def _handle_client(self, client_sock):
        """Lit les messages JSON ligne par ligne et agit."""
        with client_sock:
            buf = b""
            while not self._stop:
                data = client_sock.recv(1024)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    # On tente de décoder le JSON
                    try:
                        message = json.loads(line.decode("utf-8"))
                        self._handle_detection(message)
                    except json.JSONDecodeError:
                        print("[CameraControlServer] Erreur JSON:", line)

    def _handle_detection(self, detection):
        """
        Méthode appelée pour chaque détection reçue.
        On récupère (x_center, y_center) et on les envoie au PID.
        """
        label = detection.get("label", "unknown")
        conf = detection.get("confidence", 0.0)
        x = detection.get("x_center", 0.5)  # Valeur par défaut = centre
        y = detection.get("y_center", 0.5)

        print(f"[CameraControlServer] Reçu: label={label}, "
              f"confidence={conf:.2f}, x={x:.2f}, y={y:.2f}")

        # Mettre à jour les coordonnées du barycentre dans user_data
        self.user_data.barycentre_x = x
        self.user_data.barycentre_y = y

        # Créez une détection factice pour tester
        detection = Detection(label, conf, x, y)
        detections = [detection]

        # Mise à jour de la position de la caméra
        self.camera_deplacement.update_position(detections, self.user_data)

class Detection:
    def __init__(self, label, confidence, x_center, y_center):
        self.label = label
        self.confidence = confidence
        self.x_center = x_center
        self.y_center = y_center

    def get_label(self):
        return self.label

    def get_confidence(self):
        return self.confidence

    def get_bbox(self):
        # Retourne une boîte englobante factice pour tester
        return BBox(self.x_center, self.y_center)

class BBox:
    def __init__(self, x_center, y_center):
        self.x_center = x_center
        self.y_center = y_center

    def xmin(self):
        return self.x_center - 0.05

    def ymin(self):
        return self.y_center - 0.05

    def xmax(self):
        return self.x_center + 0.05

    def ymax(self):
        return self.y_center + 0.05


def main():
    server = CameraControlServer()
    server.start()
    try:
        # On attend indéfiniment (Ctrl+C pour arrêter)
        server.thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()

if __name__ == "__main__":
    main()
