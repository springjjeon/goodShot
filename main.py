import sys
import cv2
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QFileDialog, QSizePolicy
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer

class GolfTrackerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Good Shot - Golf Ball Tracker')
        self.setGeometry(100, 100, 800, 600)

        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # Video display label
        self.video_label = QLabel("비디오를 불러오려면 '비디오 열기' 버튼을 클릭하세요.")
        self.video_label.setStyleSheet("border: 1px solid black; background-color: #f0f0f0;")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        # 비디오 영역이 가장 넓은 공간을 차지하도록 stretch를 높게 설정합니다.
        self.main_layout.addWidget(self.video_label, stretch=4)

        # 우측 제어판 영역 레이아웃
        self.control_layout = QVBoxLayout()
        
        # Controls instructions label (세로 레이아웃에 맞게 줄바꿈 추가)
        self.info_label = QLabel("조작법:\n\n[Space] 재생/일시정지\n[◀] 이전 프레임\n[▶] 다음 프레임")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #555; font-weight: bold; margin-bottom: 20px;")
        self.control_layout.addWidget(self.info_label)

        # Buttons
        self.load_button = QPushButton("비디오 열기")
        self.play_button = QPushButton("재생 (Space)")
        self.play_button.setEnabled(False) # Disable until video is loaded

        self.control_layout.addWidget(self.load_button)
        self.control_layout.addWidget(self.play_button)
        
        # 상단 정렬을 유지하기 위해 아래에 빈 공간(stretch) 추가
        self.control_layout.addStretch()
        
        # 메인 레이아웃의 우측에 제어판 레이아웃 추가
        self.main_layout.addLayout(self.control_layout, stretch=1)

        # Instance variables
        self.video_capture = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self.is_playing = False
        
        # Connect signals
        self.load_button.clicked.connect(self.load_video)
        self.play_button.clicked.connect(self.toggle_playback)

        # 키보드 이벤트를 정상적으로 받기 위해 포커스 정책 설정
        self.setFocusPolicy(Qt.StrongFocus)

    def load_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "비디오 열기", "", "Video Files (*.mp4 *.avi *.mov)")
        if file_path:
            self.video_capture = cv2.VideoCapture(file_path)
            if not self.video_capture.isOpened():
                self.video_label.setText("비디오를 여는 데 실패했습니다.")
                return
            
            # 비디오를 불러오면 첫 프레임으로 초기화
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.video_capture.read()
            if ret:
                self.display_frame(frame)
                self.play_button.setEnabled(True)
                self.is_playing = False
                self.play_button.setText("재생 (Space)")
            else:
                self.video_label.setText("비디오 프레임을 읽는 데 실패했습니다.")
            
            # 파일 다이얼로그가 닫힌 후 메인 창으로 키보드 포커스 반환
            self.setFocus()

    def toggle_playback(self):
        if self.video_capture is None or not self.video_capture.isOpened():
            return

        if self.is_playing:
            self.timer.stop()
            self.is_playing = False
            self.play_button.setText("재생 (Space)")
        else:
            fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            if fps == 0:
                fps = 30 # 기본 fps 값
            interval = int(1000 / fps)
            
            self.timer.start(interval)
            self.is_playing = True
            self.play_button.setText("일시정지 (Space)")
        
        # 버튼 클릭 후에도 키보드 조작이 가능하도록 포커스 유지
        self.setFocus()

    def next_frame(self):
        if self.video_capture is not None and self.video_capture.isOpened():
            ret, frame = self.video_capture.read()
            if ret:
                self.display_frame(frame)
            else:
                # 비디오가 끝난 경우 타이머 중지 및 상태 초기화
                self.timer.stop()
                self.is_playing = False
                self.play_button.setText("재생 (Space)")
                
                # 비디오의 위치를 처음으로 되돌림
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.video_capture.read()
                if ret:
                    self.display_frame(frame)

    def prev_frame(self):
        if self.video_capture is not None and self.video_capture.isOpened():
            # 현재 프레임 인덱스 가져오기
            current_frame = self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)
            
            # cv2.read()는 프레임을 읽은 후 자동으로 포인터를 1 증가시키므로,
            # 이전 프레임을 보려면 현재 위치에서 2만큼 뒤로 돌아가서 읽어야 함.
            target_frame = max(0, current_frame - 2)
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
            ret, frame = self.video_capture.read()
            if ret:
                self.display_frame(frame)

    def keyPressEvent(self, event):
        # 비디오가 로드되어 있을 때만 단축키 동작
        if self.video_capture is not None and self.video_capture.isOpened():
            if event.key() == Qt.Key_Space:
                self.toggle_playback()
            elif event.key() == Qt.Key_Left:
                if self.is_playing:
                    self.toggle_playback() # 탐색 시 재생 일시정지
                self.prev_frame()
            elif event.key() == Qt.Key_Right:
                if self.is_playing:
                    self.toggle_playback() # 탐색 시 재생 일시정지
                self.next_frame()

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
