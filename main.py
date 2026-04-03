import sys
import cv2
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QFileDialog
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt

class GolfTrackerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Good Shot - Golf Ball Tracker')
        self.setGeometry(100, 100, 800, 600)

        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Video display label
        self.video_label = QLabel("비디오를 불러오려면 '비디오 열기' 버튼을 클릭하세요.")
        self.video_label.setStyleSheet("border: 1px solid black; background-color: #f0f0f0;")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.video_label)

        # Button layout
        self.button_layout = QHBoxLayout()
        
        self.load_button = QPushButton("비디오 열기")
        self.process_button = QPushButton("분석 시작")
        self.process_button.setEnabled(False) # Disable until video is loaded

        self.button_layout.addWidget(self.load_button)
        self.button_layout.addWidget(self.process_button)
        
        self.main_layout.addLayout(self.button_layout)

        # Instance variables
        self.video_capture = None
        
        # Connect signals
        self.load_button.clicked.connect(self.load_video)

    def load_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "비디오 열기", "", "Video Files (*.mp4 *.avi *.mov)")
        if file_path:
            self.video_capture = cv2.VideoCapture(file_path)
            if not self.video_capture.isOpened():
                self.video_label.setText("비디오를 여는 데 실패했습니다.")
                return
            
            # Read and display the first frame
            ret, frame = self.video_capture.read()
            if ret:
                self.display_frame(frame)
                self.process_button.setEnabled(True)
            else:
                self.video_label.setText("비디오 프레임을 읽는 데 실패했습니다.")

    def display_frame(self, frame):
        # Convert OpenCV frame (BGR) to QImage (RGB)
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Scale pixmap to fit the label while maintaining aspect ratio
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled_pixmap)


def main():
    app = QApplication(sys.argv)
    window = GolfTrackerApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
