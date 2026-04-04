import sys
import os
import cv2
import numpy as np
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QFileDialog, QSizePolicy, QCheckBox, QSlider, QStyle, QMessageBox
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer, QEvent

class ClickableSlider(QSlider):
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            # QStyle을 이용해 클릭한 마우스 좌표(x)를 정확한 슬라이더 값으로 변환
            val = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), event.x(), self.width())
            self.setValue(val)

class GolfTrackerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Good Shot - Golf Ball Tracker')
        self.setGeometry(100, 100, 800, 600)

        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # ---------------------------------------------------------
        # 좌측 영역 (비디오 + 타임라인)
        # ---------------------------------------------------------
        self.left_layout = QVBoxLayout()
        
        # Video display label
        self.video_label = QLabel("비디오를 불러오려면 '비디오 열기' 버튼을 클릭하세요.")
        self.video_label.setStyleSheet("border: 1px solid black; background-color: #f0f0f0;")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.left_layout.addWidget(self.video_label, stretch=1)
        
        # 타임라인 레이아웃
        self.timeline_layout = QHBoxLayout()
        
        self.timeline_slider = ClickableSlider(Qt.Horizontal)
        self.timeline_slider.setEnabled(False)
        self.timeline_slider.setTracking(True) # 마우스로 드래그하는 동안 실시간으로 값 변경 적용
        self.timeline_slider.valueChanged.connect(self.set_position)
        self.timeline_layout.addWidget(self.timeline_slider)
        
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setFixedWidth(100)
        self.time_label.setAlignment(Qt.AlignCenter)
        self.timeline_layout.addWidget(self.time_label)
        
        self.left_layout.addLayout(self.timeline_layout)
        
        # 메인 레이아웃에 좌측 영역 추가 (가장 넓은 공간 차지)
        self.main_layout.addLayout(self.left_layout, stretch=4)

        # ---------------------------------------------------------
        # 우측 제어판 영역
        # ---------------------------------------------------------
        self.control_layout = QVBoxLayout()
        
        # Controls instructions label
        self.info_label = QLabel("조작법:\n\n[Space] 재생/일시정지\n[◀] 이전 프레임\n[▶] 다음 프레임\n\n[분석 모드 켜고]\n공을 마우스로 클릭!\n[ESC] 현재 좌표 삭제")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #555; font-weight: bold; margin-bottom: 20px;")
        self.control_layout.addWidget(self.info_label)

        # Buttons
        self.load_button = QPushButton("비디오 열기")
        self.play_button = QPushButton("재생 (Space)")
        self.play_button.setEnabled(False) # Disable until video is loaded
        
        # 분석 모드 토글 버튼 추가
        self.track_button = QPushButton("분석 모드: 끄기")
        self.track_button.setCheckable(True)
        self.track_button.setEnabled(False)

        # 궤적 보기 옵션 체크박스
        self.show_trajectory_cb = QCheckBox("궤적 전체 보기")
        self.show_trajectory_cb.setChecked(True)
        self.show_trajectory_cb.setEnabled(False)

        # 저장 및 불러오기 버튼 (외부용)
        self.save_traj_button = QPushButton("궤적 내보내기")
        self.save_traj_button.setEnabled(False)
        self.load_traj_button = QPushButton("궤적 가져오기")
        self.load_traj_button.setEnabled(False)

        # 돋보기 영역 (Magnifier)
        self.magnifier_label = QLabel("돋보기")
        self.magnifier_label.setFixedSize(150, 150)
        self.magnifier_label.setStyleSheet("border: 2px solid red; background-color: black; color: white;")
        self.magnifier_label.setAlignment(Qt.AlignCenter)

        self.control_layout.addWidget(self.load_button)
        self.control_layout.addWidget(self.play_button)
        self.control_layout.addWidget(self.track_button)
        self.control_layout.addWidget(self.show_trajectory_cb)
        self.control_layout.addWidget(self.save_traj_button)
        self.control_layout.addWidget(self.load_traj_button)
        
        # 돋보기를 제어판 하단에 추가
        self.control_layout.addSpacing(20)
        self.control_layout.addWidget(self.magnifier_label)
        self.control_layout.setAlignment(self.magnifier_label, Qt.AlignHCenter)
        
        self.control_layout.addStretch()
        self.main_layout.addLayout(self.control_layout, stretch=1)

        # Instance variables
        self.video_path = None
        self.video_capture = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self.is_playing = False
        
        # 객체 탐지용 변수
        self.is_tracking = False
        self.is_object_selected = False
        self.current_frame = None  # 원본 이미지 백업용
        self.trajectory = {}       # 프레임 인덱스를 키로 가지는 궤적 좌표 딕셔너리
        self.trajectory_modified = False  # 궤적 수정 여부 플래그
        
        # Connect signals
        self.load_button.clicked.connect(self.load_video)
        self.play_button.clicked.connect(self.toggle_playback)
        self.track_button.toggled.connect(self.toggle_tracking)
        self.show_trajectory_cb.toggled.connect(self.redraw_current_frame)
        self.save_traj_button.clicked.connect(self.export_trajectory)
        self.load_traj_button.clicked.connect(self.import_trajectory)

        self.setFocusPolicy(Qt.StrongFocus)
        
        # 돋보기 기능을 위해 마우스 트래킹 활성화 (이벤트 필터 사용)
        self.video_label.setMouseTracking(True)
        self.video_label.installEventFilter(self)

    def format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def update_timeline(self):
        if self.video_capture is not None and self.video_capture.isOpened():
            current_frame = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES))
            total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            if fps == 0:
                fps = 30
                
            self.timeline_slider.blockSignals(True)
            self.timeline_slider.setMaximum(max(0, total_frames - 1))
            self.timeline_slider.setValue(current_frame)
            self.timeline_slider.blockSignals(False)

            current_sec = current_frame / fps
            total_sec = total_frames / fps
            
            self.time_label.setText(f"{self.format_time(current_sec)} / {self.format_time(total_sec)}")

    def set_position(self, position):
        if self.video_capture is not None and self.video_capture.isOpened():
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, position)
            ret, frame = self.video_capture.read()
            if ret:
                self.current_frame = frame.copy()
                self.display_frame(self.process_frame(self.current_frame))
                self.update_timeline()
        self.setFocus()

    def load_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "비디오 열기", "", "Video Files (*.mp4 *.avi *.mov)")
        if file_path:
            self.video_path = file_path
            self.video_capture = cv2.VideoCapture(file_path)
            if not self.video_capture.isOpened():
                self.video_label.setText("비디오를 여는 데 실패했습니다.")
                return
            
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.video_capture.read()
            if ret:
                self.current_frame = frame.copy()
                self.trajectory.clear()
                self.trajectory_modified = False
                self.tracker = None
                self.is_object_selected = False
                
                # 동영상 파일명에 맞는 궤적 데이터 자동 로드
                self.auto_load_trajectory()
                
                self.display_frame(self.process_frame(frame))
                self.play_button.setEnabled(True)
                self.track_button.setEnabled(True)
                self.show_trajectory_cb.setEnabled(True)
                self.timeline_slider.setEnabled(True)
                self.save_traj_button.setEnabled(True)
                self.load_traj_button.setEnabled(True)
                self.is_playing = False
                self.play_button.setText("재생 (Space)")
                self.update_timeline()
            else:
                self.video_label.setText("비디오 프레임을 읽는 데 실패했습니다.")
            
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
                fps = 30
            interval = int(1000 / fps)
            
            self.timer.start(interval)
            self.is_playing = True
            self.play_button.setText("일시정지 (Space)")
        
        self.setFocus()

    def toggle_tracking(self, checked):
        self.is_tracking = checked
        if checked:
            self.track_button.setText("분석 모드: 켜기")
            # 분석 모드를 켜면 추적 상태 초기화
            if self.trajectory:
                self.auto_save_trajectory()  # 기존 궤적 저장
            self.trajectory.clear()
            self.trajectory_modified = False
            self.tracker = None
            self.is_object_selected = False
        else:
            self.track_button.setText("분석 모드: 끄기")
            
        self.redraw_current_frame()

    def redraw_current_frame(self):
        """정지 상태에서 UI 옵션이 바뀌면 현재 프레임을 다시 그립니다."""
        if not self.is_playing and self.video_capture is not None and self.video_capture.isOpened():
            if self.current_frame is not None:
                self.display_frame(self.process_frame(self.current_frame))
        self.setFocus()

    def get_trajectory_file_path(self, video_path):
        """비디오 파일명을 기반으로 궤적 파일 경로를 생성합니다."""
        if not video_path:
            return None
        
        video_dir = os.path.dirname(video_path)
        video_name = os.path.basename(video_path)
        video_name_without_ext = os.path.splitext(video_name)[0]
        
        # videos 폴더 내에 {비디오파일명}_trajectory.json 으로 저장
        traj_file = os.path.join(video_dir, f"{video_name_without_ext}_trajectory.json")
        return traj_file

    def auto_load_trajectory(self):
        """비디오 경로에 맞는 궤적 파일을 자동으로 로드합니다."""
        if not self.video_path:
            return
        
        traj_file = self.get_trajectory_file_path(self.video_path)
        if traj_file and os.path.exists(traj_file):
            try:
                with open(traj_file, 'r') as f:
                    data = json.load(f)
                    # JSON keys are strings, convert to int
                    self.trajectory = {int(k): tuple(v) for k, v in data.items()}
                self.is_object_selected = True if self.trajectory else False
                self.trajectory_modified = False
                print(f"궤적 자동 로드됨: {traj_file}")
            except Exception as e:
                print(f"궤적 자동 로드 실패: {e}")

    def auto_save_trajectory(self):
        """궤적을 비디오 경로에 맞게 자동으로 저장합니다."""
        if not self.video_path or not self.trajectory:
            return
        
        traj_file = self.get_trajectory_file_path(self.video_path)
        if traj_file:
            try:
                with open(traj_file, 'w') as f:
                    json.dump(self.trajectory, f, indent=2)
                self.trajectory_modified = False
                print(f"궤적 자동 저장됨: {traj_file}")
            except Exception as e:
                print(f"궤적 자동 저장 실패: {e}")

    def export_trajectory(self):
        """궤적을 외부 JSON 파일로 내보냅니다."""
        if not self.trajectory:
            QMessageBox.warning(self, "경고", "저장할 궤적이 없습니다.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(self, "궤적 내보내기", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(self.trajectory, f, indent=2)
                QMessageBox.information(self, "완료", f"궤적이 저장되었습니다.\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"저장 실패: {e}")
            self.setFocus()

    def import_trajectory(self):
        """외부 JSON 파일에서 궤적을 불러옵니다."""
        file_path, _ = QFileDialog.getOpenFileName(self, "궤적 불러오기", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # JSON keys are strings, convert to int
                    self.trajectory = {int(k): tuple(v) for k, v in data.items()}
                self.is_object_selected = True if self.trajectory else False
                self.trajectory_modified = True
                self.redraw_current_frame()
                QMessageBox.information(self, "완료", f"궤적이 로드되었습니다.\n프레임 수: {len(self.trajectory)}")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"로드 실패: {e}")
            self.setFocus()

    def eventFilter(self, source, event):
        # 비디오 라벨 위에서 마우스가 움직일 때 돋보기 기능 수행
        if source == self.video_label and event.type() == QEvent.MouseMove:
            if self.is_tracking and self.current_frame is not None:
                pos = event.pos()
                x, y = pos.x(), pos.y()
                
                pixmap = self.video_label.pixmap()
                if pixmap is not None:
                    pw, ph = pixmap.width(), pixmap.height()
                    lw, lh = self.video_label.width(), self.video_label.height()

                    offset_x = (lw - pw) / 2
                    offset_y = (lh - ph) / 2

                    if offset_x <= x <= offset_x + pw and offset_y <= y <= offset_y + ph:
                        frame_h, frame_w = self.current_frame.shape[:2]
                        click_img_x = int((x - offset_x) * (frame_w / pw))
                        click_img_y = int((y - offset_y) * (frame_h / ph))
                        
                        # 돋보기로 보여줄 영역 크기 (원본 영상에서 40x40 픽셀을 잘라냄 -> 더 크게 확대됨)
                        box_size = 40
                        x1 = max(0, click_img_x - box_size // 2)
                        y1 = max(0, click_img_y - box_size // 2)
                        x2 = min(frame_w, click_img_x + box_size // 2)
                        y2 = min(frame_h, click_img_y + box_size // 2)
                        
                        roi = self.current_frame[y1:y2, x1:x2].copy()
                        
                        if roi.size > 0:
                            # 십자선 그리기 (초록색)
                            rh, rw = roi.shape[:2]
                            cv2.line(roi, (rw//2, 0), (rw//2, rh), (0, 255, 0), 1)
                            cv2.line(roi, (0, rh//2), (rw, rh//2), (0, 255, 0), 1)
                            
                            rgb_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
                            qt_image = QImage(rgb_roi.data, rw, rh, rw * 3, QImage.Format_RGB888)
                            
                            # 돋보기 창 크기(150x150)에 맞춰 강제로 확대
                            zoom_pixmap = QPixmap.fromImage(qt_image).scaled(150, 150, Qt.KeepAspectRatio, Qt.FastTransformation)
                            self.magnifier_label.setPixmap(zoom_pixmap)
            else:
                self.magnifier_label.clear()
                self.magnifier_label.setText("돋보기")
                            
        return super().eventFilter(source, event)

    def mousePressEvent(self, event):
        # 비디오가 로드되어 있고 분석 모드가 켜져있을 때만 마우스 클릭 처리
        if not self.is_tracking or self.current_frame is None:
            super().mousePressEvent(event)
            return

        # 메인 창 기준 클릭 좌표를 video_label 기준 좌표로 변환
        label_pos = self.video_label.mapFrom(self, event.pos())
        if self.video_label.rect().contains(label_pos):
            self.init_tracker_from_click(label_pos.x(), label_pos.y())

    def init_tracker_from_click(self, x, y):
        """QLabel을 클릭한 좌표를 영상의 실제 좌표로 변환하여 해당 프레임의 공 위치로 저장합니다."""
        pixmap = self.video_label.pixmap()
        if pixmap is None:
            return

        # 라벨 및 픽스맵(화면에 보이는 이미지) 크기
        pw, ph = pixmap.width(), pixmap.height()
        lw, lh = self.video_label.width(), self.video_label.height()

        # 라벨 내에서 이미지가 그려지는 오프셋(여백) 계산
        offset_x = (lw - pw) / 2
        offset_y = (lh - ph) / 2

        # 클릭한 위치가 화면 내 이미지 영역인지 확인
        if offset_x <= x <= offset_x + pw and offset_y <= y <= offset_y + ph:
            # 원본 영상 해상도
            frame_h, frame_w = self.current_frame.shape[:2]

            # 화면 상의 좌표를 실제 영상의 좌표 비율로 변환
            click_img_x = int((x - offset_x) * (frame_w / pw))
            click_img_y = int((y - offset_y) * (frame_h / ph))

            # 현재 프레임 인덱스 가져오기
            current_frame_idx = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            if current_frame_idx < 0:
                current_frame_idx = 0

            # 사용자가 클릭한 정확한 좌표를 딕셔너리에 저장 (돋보기를 믿고 자동 보정 제거)
            self.trajectory[current_frame_idx] = (click_img_x, click_img_y)
            self.is_object_selected = True
            self.trajectory_modified = True
            
            # 궤적 자동 저장
            self.auto_save_trajectory()

            # 화면 즉시 갱신
            self.display_frame(self.process_frame(self.current_frame))

    def process_frame(self, frame):
        """수동으로 입력된 좌표를 기반으로 마커와 궤적을 그립니다."""
        if not self.is_tracking:
            return frame
            
        display_frame = frame.copy()
        current_frame_idx = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        if current_frame_idx < 0:
            current_frame_idx = 0
            
        # 1. 현재 프레임에 저장된 좌표가 있다면 강조 표시
        if current_frame_idx in self.trajectory:
            center = self.trajectory[current_frame_idx]
            cv2.circle(display_frame, center, 10, (0, 255, 0), 2)
            cv2.circle(display_frame, center, 2, (0, 0, 255), -1)
        else:
            # 아직 좌표가 없을 때의 안내 문구
            cv2.putText(display_frame, "Click on the ball to set position!", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                
        # 2. 궤적 그리기 (체크박스 옵션에 따라 전체 선 연결)
        if self.show_trajectory_cb.isChecked() and self.trajectory:
            # 프레임 순서대로 정렬
            sorted_frames = sorted(self.trajectory.keys())
            points = [self.trajectory[idx] for idx in sorted_frames]
            
            if len(points) < 3:
                # 점이 1~2개일 때는 직선으로 연결
                for i in range(1, len(points)):
                    cv2.line(display_frame, points[i-1], points[i], (255, 0, 0), 2)
            else:
                try:
                    from scipy.interpolate import splprep, splev
                    pts = np.array(points, dtype=float)
                    
                    # 스플라인 차수 (최대 3차)
                    k = min(3, len(points) - 1)
                    
                    # s: 평활화 파라미터 (Smoothing condition).
                    # 너무 크면(polyfit처럼) 좌표와 동떨어진 선이 그려지고, 
                    # 너무 작으면 마우스 수전증 때문에 선이 꼬불꼬불해집니다.
                    # 점 개수 * 10 정도로 설정하면, 각 점에서 평균 약 3픽셀(루트10) 정도의 오차만 
                    # 허용하며 가장 이상적이고 예쁜 포물선 궤적을 쫀득하게 그려냅니다.
                    smoothing_factor = len(points) * 10
                    
                    # x, y 좌표를 매개변수 곡선으로 스플라인 피팅
                    tck, u = splprep([pts[:, 0], pts[:, 1]], s=smoothing_factor, k=k)
                    
                    # 부드러운 곡선을 그리기 위해 구간을 300개로 나눔
                    u_new = np.linspace(0, 1, 300)
                    x_new, y_new = splev(u_new, tck)
                    
                    smooth_pts = np.column_stack((x_new, y_new))
                    
                    # OpenCV polylines 함수를 사용하기 위해 배열 형태 변환 및 정수화
                    curve_points = np.int32(smooth_pts).reshape((-1, 1, 2))
                    
                    # 파란색 부드러운 궤적 그리기
                    cv2.polylines(display_frame, [curve_points], False, (255, 0, 0), 2)
                except Exception as e:
                    print(f"Curve fitting error: {e}")
                    # 피팅 실패 시 대비 기존 직선 연결
                    for i in range(1, len(points)):
                        cv2.line(display_frame, points[i-1], points[i], (255, 0, 0), 2)
                    
        return display_frame

    def next_frame(self):
        if self.video_capture is not None and self.video_capture.isOpened():
            ret, frame = self.video_capture.read()
            if ret:
                self.current_frame = frame.copy()
                self.display_frame(self.process_frame(frame))
                self.update_timeline()
            else:
                self.timer.stop()
                self.is_playing = False
                self.play_button.setText("재생 (Space)")
                
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.video_capture.read()
                if ret:
                    self.current_frame = frame.copy()
                    # 루프 재시작 시 궤적 유지
                    self.display_frame(self.process_frame(frame))
                    self.update_timeline()

    def prev_frame(self):
        if self.video_capture is not None and self.video_capture.isOpened():
            current_frame_idx = self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)
            
            target_frame_idx = max(0, current_frame_idx - 2)
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame_idx)
            
            ret, frame = self.video_capture.read()
            if ret:
                self.current_frame = frame.copy()
                # 역재생 시 추적기의 정확도가 떨어지므로 여기선 궤적 저장을 생략하거나 단순히 화면만 보여줍니다.
                # (정확한 역추적은 추가 로직이 필요하므로 현재는 단순 이동으로 처리)
                self.display_frame(self.process_frame(frame))
                self.update_timeline()

    def keyPressEvent(self, event):
        if self.video_capture is not None and self.video_capture.isOpened():
            if event.key() == Qt.Key_Space:
                self.toggle_playback()
            elif event.key() == Qt.Key_Left:
                if self.is_playing:
                    self.toggle_playback()
                self.prev_frame()
            elif event.key() == Qt.Key_Right:
                if self.is_playing:
                    self.toggle_playback()
                self.next_frame()
            elif event.key() == Qt.Key_Escape:
                if self.is_tracking:
                    current_frame_idx = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                    if current_frame_idx < 0:
                        current_frame_idx = 0
                    if current_frame_idx in self.trajectory:
                        del self.trajectory[current_frame_idx]
                        self.trajectory_modified = True
                        self.auto_save_trajectory()
                        if self.current_frame is not None:
                            self.display_frame(self.process_frame(self.current_frame))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 창 크기가 변경될 때 비디오가 로드되어 있다면 화면 크기에 맞춰 다시 그리기
        if self.video_capture is not None and self.current_frame is not None:
            self.display_frame(self.process_frame(self.current_frame))

    def display_frame(self, frame):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
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
