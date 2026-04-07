import sys
import os
import cv2
import numpy as np
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QFileDialog, QSizePolicy, QCheckBox, QSlider, QStyle, QMessageBox, QListWidget, QListWidgetItem, QComboBox
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
        self.info_label = QLabel("조작법:\n\n[Space] 재생/일시정지\n[◀] 이전 프레임\n[▶] 다음 프레임\n\n공을 마우스로 클릭!\n[ESC] 현재 좌표 삭제")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #555; font-weight: bold; margin-bottom: 20px;")
        self.control_layout.addWidget(self.info_label)

        # Buttons
        self.load_button = QPushButton("비디오 열기")
        self.play_button = QPushButton("재생 (Space)")
        self.play_button.setEnabled(False) # Disable until video is loaded

        # 궤적 보기 옵션 체크박스
        self.show_trajectory_cb = QCheckBox("궤적 전체 보기")
        self.show_trajectory_cb.setChecked(False) # 기본값은 끄고 애니메이션을 켬
        self.show_trajectory_cb.setEnabled(False)

        # 애니메이션 모드 (Shot Tracer) 체크박스
        self.anim_mode_cb = QCheckBox("애니메이션 모드 (Shot Tracer)")
        self.anim_mode_cb.setChecked(True)
        self.anim_mode_cb.setEnabled(False)

        # 애니메이션 스타일 선택 콤보박스
        self.anim_style_combo = QComboBox()
        self.anim_style_combo.addItems([
            "기본 트레이서 (오렌지 글로우)",
            "블루 글로우 (파랑)",
            "심플 레드 (빨강)",
            "볼드 옐로우 (노랑)",
            "그린 화살표 (Arrow)",
            "네잎클로버 흩날리기",
            "레드 화살표 (Red Arrow)",
            "블루 화살표 (Blue Arrow)",
            "퍼플 화살표 (Purple Arrow)",
            "3D 화살표 (3D Arrow)"
        ])
        self.anim_style_combo.setEnabled(False)

        # 저장 및 불러오기 버튼 (외부용)
        self.save_traj_button = QPushButton("궤적 내보내기")
        self.save_traj_button.setEnabled(False)
        self.load_traj_button = QPushButton("궤적 가져오기")
        self.load_traj_button.setEnabled(False)
        
        # 스윙 데이터 대시보드 버튼
        self.dashboard_button = QPushButton("스윙 데이터 대시보드 📊")
        self.dashboard_button.setEnabled(False)
        self.dashboard_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        # 캘리브레이션 버튼
        self.calibrate_button = QPushButton("📏 영점 조절 (공 크기 기준)")
        # 캘리브레이션(영점 조절) 버튼들
        self.auto_calibrate_button = QPushButton("🤖 자동 영점 조절")
        self.auto_calibrate_button.setEnabled(False)
        self.calibrate_button = QPushButton("📏 수동 조절")
        self.calibrate_button.setEnabled(False)

        # 돋보기 영역 (Magnifier)
        self.magnifier_label = QLabel("돋보기")
        self.magnifier_label.setFixedSize(400, 400)
        self.magnifier_label.setStyleSheet("border: 2px solid red; background-color: black; color: white;")
        self.magnifier_label.setAlignment(Qt.AlignCenter)

        # 자르기 버튼 및 라벨 추가
        self.trim_start_button = QPushButton("현재를 시작으로")
        self.trim_start_button.setEnabled(False)
        self.trim_end_button = QPushButton("현재를 끝으로")
        self.trim_end_button.setEnabled(False)
        self.save_trimmed_button = QPushButton("자른 원본 영상 저장하기")
        self.save_trimmed_button.setEnabled(False)
        self.export_anim_button = QPushButton("애니메이션 포함 영상 저장하기")
        self.export_anim_button.setEnabled(False)
        self.trim_info_label = QLabel("자르기 구간: 설정 안 됨")
        self.trim_info_label.setAlignment(Qt.AlignCenter)

        self.control_layout.addWidget(self.load_button)
        self.control_layout.addWidget(self.play_button)
        self.control_layout.addWidget(self.show_trajectory_cb)
        self.control_layout.addWidget(self.anim_mode_cb)
        self.control_layout.addWidget(self.anim_style_combo)
        self.control_layout.addWidget(self.save_traj_button)
        self.control_layout.addWidget(self.load_traj_button)
        self.control_layout.addWidget(self.dashboard_button)
        self.control_layout.addWidget(self.calibrate_button)
        calib_layout = QHBoxLayout()
        calib_layout.addWidget(self.auto_calibrate_button)
        calib_layout.addWidget(self.calibrate_button)
        self.control_layout.addLayout(calib_layout)

        # 궤적 목록 리스트 추가
        self.traj_list = QListWidget()
        self.traj_list.setStyleSheet("background-color: white; border: 1px solid gray;")
        self.control_layout.addWidget(self.traj_list)
        
        # 선택된 궤적 삭제 버튼 추가
        self.delete_traj_button = QPushButton("선택한 궤적 삭제")
        self.delete_traj_button.setEnabled(False)
        self.control_layout.addWidget(self.delete_traj_button)
        
        # 자르기 UI 추가
        trim_layout = QHBoxLayout()
        trim_layout.addWidget(self.trim_start_button)
        trim_layout.addWidget(self.trim_end_button)
        self.control_layout.addLayout(trim_layout)
        self.control_layout.addWidget(self.trim_info_label)
        self.control_layout.addWidget(self.save_trimmed_button)
        self.control_layout.addWidget(self.export_anim_button)

        # 돋보기 영역 (Magnifier)
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
        self.is_tracking = False   # 트래킹/분석 모드 플래그
        self.is_object_selected = False
        self.current_frame = None  # 원본 이미지 백업용
        self.trajectory = {}       # 프레임 인덱스를 키로 가지는 궤적 좌표 딕셔너리
        self.trajectory_modified = False  # 궤적 수정 여부 플래그
        
        # 영점 조절(캘리브레이션) 변수
        self.is_calibrating = False
        self.calibration_points = []
        self.meters_per_pixel = 0.012  # 기본값 (1픽셀당 1.2cm)

        # 자르기 구간 변수
        self.trim_start_frame = 0
        self.trim_end_frame = -1

        # Connect signals
        self.load_button.clicked.connect(self.load_video)
        self.play_button.clicked.connect(self.toggle_playback)
        self.show_trajectory_cb.toggled.connect(self.redraw_current_frame)
        self.anim_mode_cb.toggled.connect(self.redraw_current_frame)
        self.anim_style_combo.currentIndexChanged.connect(self.redraw_current_frame)
        self.save_traj_button.clicked.connect(self.export_trajectory)
        self.load_traj_button.clicked.connect(self.import_trajectory)
        self.dashboard_button.clicked.connect(self.show_dashboard)
        self.auto_calibrate_button.clicked.connect(self.auto_calibrate)
        self.calibrate_button.clicked.connect(self.start_calibration)
        self.traj_list.itemClicked.connect(self.on_traj_item_clicked)
        self.delete_traj_button.clicked.connect(self.delete_selected_trajectory)
        self.trim_start_button.clicked.connect(self.set_trim_start)
        self.trim_end_button.clicked.connect(self.set_trim_end)
        self.save_trimmed_button.clicked.connect(self.save_trimmed_video)
        self.export_anim_button.clicked.connect(self.export_anim_video)

        self.setFocusPolicy(Qt.StrongFocus)
        
        # 돋보기 기능을 위해 마우스 트래킹 활성화 (이벤트 필터 사용)
        self.video_label.setMouseTracking(True)
        self.video_label.installEventFilter(self)

    def format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def update_traj_list(self):
        """궤적 리스트 UI를 갱신합니다."""
        self.traj_list.clear()
        if not self.trajectory:
            return
            
        fps = 30
        if self.video_capture is not None and self.video_capture.isOpened():
            fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            if fps == 0: fps = 30

        for frame_idx in sorted(self.trajectory.keys()):
            x, y = self.trajectory[frame_idx]
            time_sec = frame_idx / fps
            time_str = self.format_time(time_sec)
            item_text = f"Frame {frame_idx} ({time_str}) - X:{x}, Y:{y}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, frame_idx)
            self.traj_list.addItem(item)
            
    def on_traj_item_clicked(self, item):
        """목록에서 아이템을 클릭하면 해당 프레임으로 이동합니다."""
        frame_idx = item.data(Qt.UserRole)
        self.set_position(frame_idx)

    def delete_selected_trajectory(self):
        """목록에서 선택된 궤적을 삭제합니다."""
        current_item = self.traj_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "경고", "삭제할 궤적을 목록에서 선택해주세요.")
            return
            
        frame_idx = current_item.data(Qt.UserRole)
        
        if frame_idx in self.trajectory:
            del self.trajectory[frame_idx]
            self.trajectory_modified = True
            self.update_traj_list()
            self.auto_save_trajectory()
            
            if self.current_frame is not None:
                self.display_frame(self.process_frame(self.current_frame))
                
            print(f"궤적 삭제됨: 프레임 {frame_idx}")

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
        try:
            file_path, _ = QFileDialog.getOpenFileName(None, "비디오 열기", "", "Video Files (*.mp4 *.avi *.mov)", options=QFileDialog.DontUseNativeDialog)
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
                self.is_tracking = True
                
                # 동영상 파일명에 맞는 궤적 데이터 자동 로드
                self.auto_load_trajectory()
                
                self.display_frame(self.process_frame(frame))
                self.play_button.setEnabled(True)
                self.show_trajectory_cb.setEnabled(True)
                self.anim_mode_cb.setEnabled(True)
                self.anim_style_combo.setEnabled(True)
                self.timeline_slider.setEnabled(True)
                self.save_traj_button.setEnabled(True)
                self.load_traj_button.setEnabled(True)
                self.dashboard_button.setEnabled(True)
                self.auto_calibrate_button.setEnabled(True)
                self.calibrate_button.setEnabled(True)
                self.delete_traj_button.setEnabled(True)

                self.trim_start_button.setEnabled(True)
                self.trim_end_button.setEnabled(True)
                self.save_trimmed_button.setEnabled(True)
                self.export_anim_button.setEnabled(True)
                
                total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                self.trim_start_frame = 0
                self.trim_end_frame = max(0, total_frames - 1)
                self.trim_info_label.setText(f"자르기 구간: {self.trim_start_frame} ~ {self.trim_end_frame}")

                self.is_playing = False
                self.play_button.setText("재생 (Space)")
                self.update_timeline()
            else:
                self.video_label.setText("비디오 프레임을 읽는 데 실패했습니다.")
            
            self.setFocus()
        except Exception as e:
            QMessageBox.critical(None, "오류", f"비디오 로드 실패: {e}")

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
                    # JSON keys are strings, convert to int, ensure coordinates are int
                    self.trajectory = {int(k): (int(v[0]), int(v[1])) for k, v in data.items()}
                self.is_object_selected = True if self.trajectory else False
                self.trajectory_modified = False
                self.update_traj_list()
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
        
        file_path, _ = QFileDialog.getSaveFileName(self, "궤적 내보내기", "", "JSON Files (*.json)", options=QFileDialog.DontUseNativeDialog)
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
        try:
            file_path, _ = QFileDialog.getOpenFileName(None, "궤적 불러오기", "", "JSON Files (*.json)", options=QFileDialog.DontUseNativeDialog)
            if file_path:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # JSON keys are strings, convert to int, ensure coordinates are int
                    self.trajectory = {int(k): (int(v[0]), int(v[1])) for k, v in data.items()}
                self.is_object_selected = True if self.trajectory else False
                self.trajectory_modified = True
                self.update_traj_list()
                self.redraw_current_frame()
                QMessageBox.information(None, "완료", f"궤적이 로드되었습니다.\n프레임 수: {len(self.trajectory)}")
                self.setFocus()
        except Exception as e:
            QMessageBox.critical(self, "오류", f"로드 실패: {e}")

    def auto_calibrate(self):
        import math
        if not self.trajectory:
            QMessageBox.warning(self, "경고", "먼저 화면에서 공을 클릭해 궤적을 1개 이상 입력해주세요.")
            return

        first_frame_idx = min(self.trajectory.keys())
        bx, by = self.trajectory[first_frame_idx]

        # 해당 프레임 읽어오기
        current_pos = self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, first_frame_idx)
        ret, frame = self.video_capture.read()
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, current_pos) # 원래 위치 복구

        if not ret:
            QMessageBox.warning(self, "오류", "해당 프레임을 읽을 수 없습니다.")
            return

        # 공 주변 40x40 픽셀 영역 잘라내기
        box_size = 40
        h, w = frame.shape[:2]
        x1 = max(0, bx - box_size // 2)
        y1 = max(0, by - box_size // 2)
        x2 = min(w, bx + box_size // 2)
        y2 = min(h, by + box_size // 2)

        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # 1차 시도: Hough 원 변환(HoughCircles) 알고리즘으로 동그란 형태 탐지
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=10,
                                   param1=50, param2=15, minRadius=2, maxRadius=15)
        
        best_radius = 0
        cx_roi, cy_roi = bx - x1, by - y1

        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            min_dist = float('inf')
            for (x, y, r) in circles:
                dist = math.hypot(x - cx_roi, y - cy_roi)
                if dist < min_dist:
                    min_dist = dist
                    best_radius = r
            # 클릭한 곳과 중심이 너무 멀면 오인식으로 간주
            if min_dist > 10:
                best_radius = 0

        # 2차 시도: 원 변환 실패 시 밝기 기준 외곽선(Contours) 검출
        if best_radius == 0:
            _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            min_dist = float('inf')
            for cnt in contours:
                (x, y), radius = cv2.minEnclosingCircle(cnt)
                dist = math.hypot(x - cx_roi, y - cy_roi)
                if dist < 15 and 1 < radius < 20:
                    if dist < min_dist:
                        min_dist = dist
                        best_radius = radius

        if best_radius > 0:
            dist_px = best_radius * 2
            self.meters_per_pixel = 0.04267 / dist_px
            QMessageBox.information(self, "자동 영점 조절 완료", 
                                    f"궤적 시작점의 골프공 크기를 자동으로 인식했습니다!\n\n"
                                    f"인식된 직경: {dist_px:.1f} 픽셀\n"
                                    f"1픽셀당 비율: {self.meters_per_pixel*100:.2f} cm")
        else:
            QMessageBox.warning(self, "자동 인식 실패", 
                                "골프공을 명확히 찾지 못했습니다.\n"
                                "배경과 공의 색상이 비슷하거나 크기가 너무 작을 수 있습니다.\n"
                                "'수동 조절' 버튼을 이용해주세요.")

    def start_calibration(self):
        self.is_calibrating = True
        self.calibration_points = []
        QMessageBox.information(self, "영점 조절 시작", "영상(또는 돋보기)에 보이는 골프공의 지름을 측정합니다.\n\n공의 왼쪽 끝과 오른쪽 끝을 각각 마우스로 1번씩(총 2번) 클릭해주세요.")
        self.setFocus()

    def show_dashboard(self):
        import math
        if len(self.trajectory) < 3:
            QMessageBox.warning(self, "데이터 부족", "정확한 분석을 위해 최소 3개 이상의 궤적 점이 필요합니다.")
            return

        fps = 30
        if self.video_capture is not None and self.video_capture.isOpened():
            fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            if fps == 0: fps = 30

        frames = sorted(self.trajectory.keys())
        points = [self.trajectory[f] for f in frames]

        # 1. 발사각 (Launch Angle)
        p0 = points[0]
        # 노이즈를 줄이기 위해 시작점에서 3프레임 또는 1/10 지점의 좌표 사용
        idx_launch = min(3, max(1, len(points) // 10))
        p_launch = points[idx_launch]
        
        dx = p_launch[0] - p0[0]
        dy = p0[1] - p_launch[1] # 화면 Y는 아래로 갈수록 커지므로 반전

        # 지면 대비 절대 발사각 (진행 방향에 상관없이 위로 향하는 각도)
        launch_angle = math.degrees(math.atan2(dy, abs(dx))) if dx != 0 else (90.0 if dy > 0 else -90.0)
        direction = "우측" if dx > 0 else "좌측" if dx < 0 else "수직"

        # 속도 추정 (Ball Speed & Swing Speed)
        dist_px = math.hypot(dx, dy)
        time_elapsed = (frames[idx_launch] - frames[0]) / fps
        
        # 캘리브레이션된 픽셀 당 미터 값 사용 (기본값 0.012)
        meters_per_pixel = getattr(self, 'meters_per_pixel', 0.012)
        
        if time_elapsed > 0:
            # 2D 카메라(특히 타겟 방향을 바라보는 후방 DTL 구도)에서는 공이 화면 안쪽(Z축)으로 날아갑니다.
            # 화면상의 X, Y 픽셀 이동량만 계산하면 실제 이동 거리의 1/5 수준으로 측정되므로 3D 원근 보정 계수를 곱해줍니다.
            perspective_compensation = 5.5
            ball_speed_mps = ((dist_px * meters_per_pixel) / time_elapsed) * perspective_compensation
            
            # 스매시 팩터(Smash Factor) 1.45를 가정하여 클럽 헤드 스피드 역산
            swing_speed_mps = ball_speed_mps / 1.45
        else:
            ball_speed_mps = 0.0
            swing_speed_mps = 0.0

        # 2. 최고점 (Apex) 및 체공 시간
        y_coords = [p[1] for p in points]
        apex_idx = y_coords.index(min(y_coords))
        apex_frame = frames[apex_idx]
        apex_time = (apex_frame - frames[0]) / fps
        hang_time = (frames[-1] - frames[0]) / fps

        # 3. 구질 분석 (Shot Shape)
        p_end = points[-1]
        v1_x = p_end[0] - p0[0]
        v1_y = p_end[1] - p0[1]
        v1_len = math.hypot(v1_x, v1_y)
        
        avg_deviation = 0
        if v1_len > 0:
            curve_sum = 0
            for p in points:
                v2_x = p[0] - p0[0]
                v2_y = p[1] - p0[1]
                # 외적(Cross Product)으로 치우침 거리 계산
                cross = v1_x * v2_y - v1_y * v2_x
                curve_sum += cross
            
            # 평균 치우침 픽셀 거리
            avg_deviation = curve_sum / (v1_len * len(points))

        # 영상 촬영 구도(정면 vs 후방) 자동 판별
        # 공이 가로(X)로 이동한 거리가 세로(Y) 이동 거리보다 확연히 크면 정면(Face-On) 영상으로 간주
        if abs(v1_x) > abs(v1_y) * 1.2:
            shot_shape = "분석 불가 (정면/측면 구도 영상)"
        else:
            # 후방(DTL) 영상 기준 해석 (마우스 클릭 오차를 감안해 임계값을 10픽셀로 둔감화)
            if avg_deviation > 10:
                shot_shape = "화면 우측 휨 (페이드/슬라이스 추정)"
            elif avg_deviation < -10:
                shot_shape = "화면 좌측 휨 (드로우/훅 추정)"
            else:
                shot_shape = "스트레이트 (직진 추정)"

        report = (
            f"📊 [스윙 데이터 추정 대시보드]\n\n"
            f"🎯 타구 방향: 화면 {direction}\n"
            f"📐 초기 발사각: {launch_angle:.1f}°\n"
            f"🚀 추정 볼 스피드: 약 {ball_speed_mps:.1f} m/s\n"
            f"🏌️ 추정 스윙 스피드: 약 {swing_speed_mps:.1f} m/s\n"
            f"⏱️ 최고점 도달: {apex_time:.2f}초 (프레임 {apex_frame})\n"
            f"⏳ 총 체공 시간: {hang_time:.2f}초\n"
            f"🌪️ 비행 궤적: {shot_shape}\n\n"
            f"*위 데이터는 2D 화면상의 픽셀 좌표를 기반으로 계산된\n"
            f"추정치이므로 실제 수치(센서 측정값)와는 다를 수 있습니다."
        )

        QMessageBox.information(self, "스윙 데이터 대시보드", report)

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
                        
                        # 돋보기로 보여줄 영역 크기 (원본 영상에서 100x100 픽셀을 잘라냄)
                        box_size = 100
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
                            
                            # 돋보기 창 크기(400x400)에 맞춰 강제로 확대
                            zoom_pixmap = QPixmap.fromImage(qt_image).scaled(400, 400, Qt.KeepAspectRatio, Qt.FastTransformation)
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

            # 캘리브레이션(영점 조절) 모드일 경우
            if getattr(self, 'is_calibrating', False):
                import math
                self.calibration_points.append((click_img_x, click_img_y))
                if len(self.calibration_points) == 2:
                    p1 = self.calibration_points[0]
                    p2 = self.calibration_points[1]
                    dist_px = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
                    if dist_px > 0:
                        # 실제 골프공 지름은 약 4.267cm (0.04267m)
                        self.meters_per_pixel = 0.04267 / dist_px
                        QMessageBox.information(self, "영점 조절 완료", f"골프공 지름이 {dist_px:.1f} 픽셀로 측정되었습니다.\n\n이제 1픽셀당 {self.meters_per_pixel*100:.2f}cm 의 비율을 바탕으로 더 정확한 스피드가 계산됩니다!")
                    else:
                        QMessageBox.warning(self, "오류", "서로 다른 두 점을 클릭해주세요.")
                    self.is_calibrating = False
                    self.calibration_points = []
                self.display_frame(self.process_frame(self.current_frame))
                return

            # 사용자가 클릭한 정확한 좌표를 딕셔너리에 저장 (돋보기를 믿고 자동 보정 제거)
            self.trajectory[current_frame_idx] = (click_img_x, click_img_y)
            self.is_object_selected = True
            self.trajectory_modified = True
            self.update_traj_list()
            
            # 궤적 자동 저장
            self.auto_save_trajectory()

            # 화면 즉시 갱신
            self.display_frame(self.process_frame(self.current_frame))

    def process_frame(self, frame, export_mode=False):
        """수동으로 입력된 좌표를 기반으로 마커와 궤적을 그립니다."""
        is_show_all = self.show_trajectory_cb.isChecked()
        is_anim_mode = hasattr(self, 'anim_mode_cb') and self.anim_mode_cb.isChecked()
        anim_style = self.anim_style_combo.currentIndex() if hasattr(self, 'anim_style_combo') else 0
        
        # 궤적 전체 보기와 애니메이션 모드가 모두 꺼져있다면 원본 프레임 반환
        if not is_show_all and not is_anim_mode:
            return frame
            
        display_frame = frame.copy()
        current_frame_idx = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        if current_frame_idx < 0:
            current_frame_idx = 0
            
        # 1. 현재 프레임에 저장된 좌표가 있다면 강조 표시
        if current_frame_idx in self.trajectory:
            if not export_mode:
                center = self.trajectory[current_frame_idx]
                cv2.circle(display_frame, center, 10, (0, 255, 0), 2)
                cv2.circle(display_frame, center, 2, (0, 0, 255), -1)
        else:
            if not export_mode:
                # 아직 좌표가 없을 때의 안내 문구
                cv2.putText(display_frame, "Click on the ball to set position!", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # 캘리브레이션 진행 중일 때 클릭한 첫 번째 점 시각적 표시
        if getattr(self, 'is_calibrating', False) and getattr(self, 'calibration_points', []) and not export_mode:
            pt = self.calibration_points[0]
            cv2.circle(display_frame, pt, 4, (0, 255, 255), -1)
            cv2.putText(display_frame, "Click the other side of the ball", (pt[0] + 15, pt[1]), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
        # 2. 궤적 그리기 (체크박스 옵션에 따라 선 연결)
        if (is_show_all or is_anim_mode) and self.trajectory:
            all_sorted_frames = sorted(self.trajectory.keys())
            all_points = [self.trajectory[idx] for idx in all_sorted_frames]
            
            if len(all_points) < 3:
                # 점이 1~2개일 때는 직선으로 연결
                if is_show_all:
                    for i in range(1, len(all_points)):
                        cv2.line(display_frame, all_points[i-1], all_points[i], (255, 0, 0), 2)
                
                if is_anim_mode:
                    valid_frames = [f for f in all_sorted_frames if f <= current_frame_idx]
                    points_to_draw = [self.trajectory[idx] for idx in valid_frames]
                    for i in range(1, len(points_to_draw)):
                        if anim_style == 0:
                            cv2.line(display_frame, points_to_draw[i-1], points_to_draw[i], (0, 200, 255), 4)
                        elif anim_style == 1:
                            cv2.line(display_frame, points_to_draw[i-1], points_to_draw[i], (255, 200, 0), 4)
                        elif anim_style == 2:
                            cv2.line(display_frame, points_to_draw[i-1], points_to_draw[i], (0, 0, 255), 3)
                        elif anim_style == 3:
                            cv2.line(display_frame, points_to_draw[i-1], points_to_draw[i], (0, 255, 255), 6)
                        elif anim_style in [4, 6, 7, 8]:
                            color = (50, 205, 50) if anim_style == 4 else (0, 0, 255) if anim_style == 6 else (255, 100, 50) if anim_style == 7 else (255, 0, 255)
                            cv2.arrowedLine(display_frame, points_to_draw[i-1], points_to_draw[i], color, 4, tipLength=0.3)
                        elif anim_style == 9:
                            p1 = points_to_draw[i-1]
                            p2 = points_to_draw[i]
                            # 리얼 3D 화살표 (원기둥 파이프 꼬리 + 다면체 화살촉)
                            cv2.line(display_frame, p1, p2, (0, 60, 100), 10)
                            cv2.line(display_frame, p1, p2, (0, 120, 200), 6)
                            cv2.line(display_frame, p1, p2, (0, 180, 255), 2)
                            dist = np.hypot(p2[0]-p1[0], p2[1]-p1[1])
                            if dist > 0:
                                ux, uy = (p2[0]-p1[0])/dist, (p2[1]-p1[1])/dist
                                bc = (p2[0] - ux*25, p2[1] - uy*25)
                                left = (int(bc[0] - uy*12), int(bc[1] + ux*12))
                                right = (int(bc[0] + uy*12), int(bc[1] - ux*12))
                                ridge = (int(bc[0] - ux*5), int(bc[1] - uy*5 - 15))
                                p2_int = (int(p2[0]), int(p2[1]))
                                cv2.fillConvexPoly(display_frame, np.array([p2_int, left, ridge], dtype=np.int32), (0, 120, 200))
                                cv2.fillConvexPoly(display_frame, np.array([p2_int, right, ridge], dtype=np.int32), (0, 200, 255))
                                cv2.polylines(display_frame, [np.array([p2_int, left, ridge], dtype=np.int32)], True, (0, 80, 150), 1)
                                cv2.polylines(display_frame, [np.array([p2_int, right, ridge], dtype=np.int32)], True, (0, 150, 220), 1)
                        elif anim_style == 5:
                            cv2.line(display_frame, points_to_draw[i-1], points_to_draw[i], (144, 238, 144), 3)
                            px, py = points_to_draw[i]
                            ox = int((px * 17 + py * 31) % 41) - 20
                            oy = int((px * 23 + py * 19) % 41) - 20
                            s = int((px * 13 + py * 29) % 3) + 2
                            cx, cy = px + ox, py + oy
                            cv2.circle(display_frame, (cx - s, cy - s), s, (0, 200, 0), -1)
                            cv2.circle(display_frame, (cx + s, cy - s), s, (0, 200, 0), -1)
                            cv2.circle(display_frame, (cx - s, cy + s), s, (0, 200, 0), -1)
                            cv2.circle(display_frame, (cx + s, cy + s), s, (0, 200, 0), -1)
                            cv2.line(display_frame, (cx, cy), (cx, cy + s * 3), (0, 200, 0), 1)
            else:
                try:
                    from scipy.interpolate import splprep, splev
                    pts = np.array(all_points, dtype=float)
                    
                    k = min(3, len(all_points) - 1)
                    smoothing_factor = len(all_points) * 10
                    
                    f_min = all_sorted_frames[0]
                    f_max = all_sorted_frames[-1]
                    
                    # 프레임 인덱스(시간)를 기준으로 스플라인 매개변수 u를 생성합니다.
                    # 이를 통해 궤적 생성 속도가 실제 공의 비행 속도와 일치하게 됩니다.
                    if f_max > f_min:
                        u_custom = [(f - f_min) / (f_max - f_min) for f in all_sorted_frames]
                        tck, u = splprep([pts[:, 0], pts[:, 1]], u=u_custom, s=smoothing_factor, k=k)
                    else:
                        tck, u = splprep([pts[:, 0], pts[:, 1]], s=smoothing_factor, k=k)
                    
                    # 1. 궤적 전체 그리기 (파란선)
                    if is_show_all:
                        u_full = np.linspace(0, 1, 300)
                        x_full, y_full = splev(u_full, tck)
                        full_pts = np.column_stack((x_full, y_full))
                        full_curve = np.int32(full_pts).reshape((-1, 1, 2))
                        cv2.polylines(display_frame, [full_curve], False, (255, 0, 0), 2)
                    
                    # 2. 애니메이션 (Shot Tracer) 그리기 (현재 프레임까지 길어지는 선)
                    if is_anim_mode:
                        u_max = 0.0
                        if current_frame_idx >= f_max:
                            u_max = 1.0
                        elif current_frame_idx > f_min:
                            # u 매개변수가 시간에 선형적으로 비례하므로 단순 비율로 계산 가능합니다.
                            u_max = (current_frame_idx - f_min) / (f_max - f_min)
                                    
                        if u_max > 0.0:
                            num_points = max(10, int(300 * u_max))
                            u_anim = np.linspace(0, u_max, num_points)
                            x_anim, y_anim = splev(u_anim, tck)
                            anim_pts = np.column_stack((x_anim, y_anim))
                            anim_curve = np.int32(anim_pts).reshape((-1, 1, 2))
                            
                            if anim_style == 0:
                                # 기본 트레이서 (오렌지 글로우)
                                cv2.polylines(display_frame, [anim_curve], False, (0, 100, 255), 8)
                                cv2.polylines(display_frame, [anim_curve], False, (0, 200, 255), 4)
                                cv2.polylines(display_frame, [anim_curve], False, (255, 255, 255), 2)
                            elif anim_style == 1:
                                # 블루 글로우
                                cv2.polylines(display_frame, [anim_curve], False, (255, 100, 0), 8)
                                cv2.polylines(display_frame, [anim_curve], False, (255, 200, 0), 4)
                                cv2.polylines(display_frame, [anim_curve], False, (255, 255, 255), 2)
                            elif anim_style == 2:
                                # 심플 레드
                                cv2.polylines(display_frame, [anim_curve], False, (0, 0, 255), 3)
                            elif anim_style == 3:
                                # 볼드 옐로우
                                cv2.polylines(display_frame, [anim_curve], False, (0, 255, 255), 6)
                            elif anim_style in [4, 6, 7, 8]:
                                # 화살표 효과들
                                color = (50, 205, 50) if anim_style == 4 else (0, 0, 255) if anim_style == 6 else (255, 100, 50) if anim_style == 7 else (255, 0, 255)
                                cv2.polylines(display_frame, [anim_curve], False, color, 4)
                                if len(anim_pts) >= 2:
                                    p2 = tuple(map(int, anim_pts[-1]))
                                    p1 = p2
                                    dist = 0
                                    # 화살표 방향을 자연스럽게 잡기 위해 20픽셀 정도 떨어진 이전 궤적 점을 찾음
                                    for idx in range(len(anim_pts)-2, -1, -1):
                                        pt = tuple(map(int, anim_pts[idx]))
                                        dist = np.hypot(p2[0]-pt[0], p2[1]-pt[1])
                                        if dist >= 20:
                                            p1 = pt
                                            break
                                    if p1 == p2:
                                        p1 = tuple(map(int, anim_pts[-2]))
                                        dist = np.hypot(p2[0]-p1[0], p2[1]-p1[1])
                                    tip_len = 15.0 / dist if dist > 0 else 0.5
                                    cv2.arrowedLine(display_frame, p1, p2, color, 4, tipLength=min(tip_len, 1.0))
                            elif anim_style == 9:
                                # 리얼 3D 화살표 (입체 파이프 & 다각형 화살촉)
                                cv2.polylines(display_frame, [anim_curve], False, (0, 60, 100), 10)
                                cv2.polylines(display_frame, [anim_curve], False, (0, 120, 200), 6)
                                cv2.polylines(display_frame, [anim_curve], False, (0, 180, 255), 2)
                                if len(anim_pts) >= 2:
                                    p2 = tuple(map(int, anim_pts[-1]))
                                    p1 = p2
                                    dist = 0
                                    for idx in range(len(anim_pts)-2, -1, -1):
                                        pt = tuple(map(int, anim_pts[idx]))
                                        dist = np.hypot(p2[0]-pt[0], p2[1]-pt[1])
                                        if dist >= 20:
                                            p1 = pt
                                            break
                                    if p1 == p2:
                                        p1 = tuple(map(int, anim_pts[-2]))
                                        dist = np.hypot(p2[0]-p1[0], p2[1]-p1[1])
                                    if dist > 0:
                                        ux, uy = (p2[0]-p1[0])/dist, (p2[1]-p1[1])/dist
                                        bc = (p2[0] - ux*30, p2[1] - uy*30)
                                        left = (int(bc[0] - uy*15), int(bc[1] + ux*15))
                                        right = (int(bc[0] + uy*15), int(bc[1] - ux*15))
                                        ridge = (int(bc[0] - ux*5), int(bc[1] - uy*5 - 20))
                                        cv2.fillConvexPoly(display_frame, np.array([p2, left, ridge], dtype=np.int32), (0, 120, 200))
                                        cv2.fillConvexPoly(display_frame, np.array([p2, right, ridge], dtype=np.int32), (0, 200, 255))
                                        cv2.polylines(display_frame, [np.array([p2, left, ridge], dtype=np.int32)], True, (0, 80, 150), 1)
                                        cv2.polylines(display_frame, [np.array([p2, right, ridge], dtype=np.int32)], True, (0, 150, 220), 1)
                            elif anim_style == 5:
                                # 네잎클로버 흩날리기
                                cv2.polylines(display_frame, [anim_curve], False, (144, 238, 144), 3)
                                for idx, pt in enumerate(anim_pts):
                                    if idx % 8 == 0:
                                        px, py = int(pt[0]), int(pt[1])
                                        ox = int((px * 17 + py * 31) % 41) - 20
                                        oy = int((px * 23 + py * 19) % 41) - 20
                                        s = int((px * 13 + py * 29) % 3) + 2
                                        cx, cy = px + ox, py + oy
                                        cv2.circle(display_frame, (cx - s, cy - s), s, (0, 200, 0), -1)
                                        cv2.circle(display_frame, (cx + s, cy - s), s, (0, 200, 0), -1)
                                        cv2.circle(display_frame, (cx - s, cy + s), s, (0, 200, 0), -1)
                                        cv2.circle(display_frame, (cx + s, cy + s), s, (0, 200, 0), -1)
                                        cv2.line(display_frame, (cx, cy), (cx, cy + s * 3), (0, 200, 0), 1)
                            
                except Exception as e:
                    print(f"Curve fitting error: {e}")
                    # 피팅 실패 시 직선 연결
                    if is_show_all:
                        for i in range(1, len(all_points)):
                            cv2.line(display_frame, all_points[i-1], all_points[i], (255, 0, 0), 2)
                    if is_anim_mode:
                        valid_frames = [f for f in all_sorted_frames if f <= current_frame_idx]
                        points_to_draw = [self.trajectory[idx] for idx in valid_frames]
                        for i in range(1, len(points_to_draw)):
                            if anim_style == 0:
                                cv2.line(display_frame, points_to_draw[i-1], points_to_draw[i], (0, 200, 255), 4)
                            elif anim_style == 1:
                                cv2.line(display_frame, points_to_draw[i-1], points_to_draw[i], (255, 200, 0), 4)
                            elif anim_style == 2:
                                cv2.line(display_frame, points_to_draw[i-1], points_to_draw[i], (0, 0, 255), 3)
                            elif anim_style == 3:
                                cv2.line(display_frame, points_to_draw[i-1], points_to_draw[i], (0, 255, 255), 6)
                            elif anim_style in [4, 6, 7, 8]:
                                color = (50, 205, 50) if anim_style == 4 else (0, 0, 255) if anim_style == 6 else (255, 100, 50) if anim_style == 7 else (255, 0, 255)
                                cv2.arrowedLine(display_frame, points_to_draw[i-1], points_to_draw[i], color, 4, tipLength=0.3)
                            elif anim_style == 9:
                                p1 = points_to_draw[i-1]
                                p2 = points_to_draw[i]
                                cv2.line(display_frame, p1, p2, (0, 60, 100), 10)
                                cv2.line(display_frame, p1, p2, (0, 120, 200), 6)
                                cv2.line(display_frame, p1, p2, (0, 180, 255), 2)
                                dist = np.hypot(p2[0]-p1[0], p2[1]-p1[1])
                                if dist > 0:
                                    ux, uy = (p2[0]-p1[0])/dist, (p2[1]-p1[1])/dist
                                    bc = (p2[0] - ux*25, p2[1] - uy*25)
                                    left = (int(bc[0] - uy*12), int(bc[1] + ux*12))
                                    right = (int(bc[0] + uy*12), int(bc[1] - ux*12))
                                    ridge = (int(bc[0] - ux*5), int(bc[1] - uy*5 - 15))
                                    p2_int = (int(p2[0]), int(p2[1]))
                                    cv2.fillConvexPoly(display_frame, np.array([p2_int, left, ridge], dtype=np.int32), (0, 120, 200))
                                    cv2.fillConvexPoly(display_frame, np.array([p2_int, right, ridge], dtype=np.int32), (0, 200, 255))
                                    cv2.polylines(display_frame, [np.array([p2_int, left, ridge], dtype=np.int32)], True, (0, 80, 150), 1)
                                    cv2.polylines(display_frame, [np.array([p2_int, right, ridge], dtype=np.int32)], True, (0, 150, 220), 1)
                            elif anim_style == 5:
                                cv2.line(display_frame, points_to_draw[i-1], points_to_draw[i], (144, 238, 144), 3)
                                px, py = points_to_draw[i]
                                ox = int((px * 17 + py * 31) % 41) - 20
                                oy = int((px * 23 + py * 19) % 41) - 20
                                s = int((px * 13 + py * 29) % 3) + 2
                                cx, cy = px + ox, py + oy
                                cv2.circle(display_frame, (cx - s, cy - s), s, (0, 200, 0), -1)
                                cv2.circle(display_frame, (cx + s, cy - s), s, (0, 200, 0), -1)
                                cv2.circle(display_frame, (cx - s, cy + s), s, (0, 200, 0), -1)
                                cv2.circle(display_frame, (cx + s, cy + s), s, (0, 200, 0), -1)
                                cv2.line(display_frame, (cx, cy), (cx, cy + s * 3), (0, 200, 0), 1)

        # 3. 다음 프레임 위치 예측 (현재까지의 궤적을 기반으로)
        if self.is_tracking and not export_mode:
            target_f = current_frame_idx if current_frame_idx not in self.trajectory else current_frame_idx + 1
            past_frames = [f for f in sorted(self.trajectory.keys()) if f < target_f]
            
            if len(past_frames) >= 2:
                try:
                    # 상승 시점(초반) 예측률을 높이기 위해 최근 3개 프레임만 사용 (과거 데이터로 인한 예측 지연 방지)
                    use_frames = past_frames[-3:]
                    t_data = np.array(use_frames, dtype=float)
                    points = np.array([self.trajectory[f] for f in use_frames], dtype=float)
                    
                    # 가장 최근 두 프레임 간의 속도(직선) 예측을 기본으로 함
                    f1, f2 = t_data[-2], t_data[-1]
                    p1, p2 = points[-2], points[-1]
                    
                    dt = f2 - f1
                    if dt > 0:
                        vx = (p2[0] - p1[0]) / dt
                        vy = (p2[1] - p1[1]) / dt
                    else:
                        vx, vy = 0, 0
                        
                    dt_target = target_f - f2
                    # 1차 예측 (등속도)
                    pred_x_lin = p2[0] + vx * dt_target
                    pred_y_lin = p2[1] + vy * dt_target
                    
                    pred_x, pred_y = pred_x_lin, pred_y_lin
                    
                    # 3개 이상의 프레임이 있으면 가속도를 약간 반영 (2차)
                    if len(use_frames) == 3:
                        f0 = t_data[0]
                        p0 = points[0]
                        dt0 = f1 - f0
                        if dt0 > 0:
                            vx0 = (p1[0] - p0[0]) / dt0
                            vy0 = (p1[1] - p0[1]) / dt0
                            
                            # 가속도 계산
                            ax = (vx - vx0) / ((dt + dt0) / 2)
                            ay = (vy - vy0) / ((dt + dt0) / 2)
                            
                            # 상승 시 가속도 변화가 심할 수 있으므로 가속도(곡선) 반영 비율을 낮춤 (0.3)
                            pred_x_acc = p2[0] + vx * dt_target + 0.5 * ax * (dt_target ** 2)
                            pred_y_acc = p2[1] + vy * dt_target + 0.5 * ay * (dt_target ** 2)
                            
                            pred_x = (pred_x_lin * 0.7) + (pred_x_acc * 0.3)
                            pred_y = (pred_y_lin * 0.7) + (pred_y_acc * 0.3)

                    pred_x = int(pred_x)
                    pred_y = int(pred_y)
                    
                    # 보라색 점과 십자선으로 예측 위치 표시
                    cv2.circle(display_frame, (pred_x, pred_y), 8, (255, 0, 255), 2)
                    cv2.line(display_frame, (pred_x - 10, pred_y), (pred_x + 10, pred_y), (255, 0, 255), 1)
                    cv2.line(display_frame, (pred_x, pred_y - 10), (pred_x, pred_y + 10), (255, 0, 255), 1)
                    
                    cv2.putText(display_frame, "Predicted", (pred_x + 15, pred_y - 15), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
                except Exception as e:
                    print(f"Prediction point error: {e}")
                    
        return display_frame

    def set_trim_start(self):
        if self.video_capture is not None and self.video_capture.isOpened():
            current_frame = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            if current_frame < 0: current_frame = 0
            if self.trim_end_frame != -1 and current_frame >= self.trim_end_frame:
                QMessageBox.warning(self, "경고", "시작 프레임은 끝 프레임보다 앞서야 합니다.")
                return
            self.trim_start_frame = current_frame
            self.trim_info_label.setText(f"자르기 구간: {self.trim_start_frame} ~ {self.trim_end_frame}")

    def set_trim_end(self):
        if self.video_capture is not None and self.video_capture.isOpened():
            current_frame = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            if current_frame < 0: current_frame = 0
            if current_frame <= self.trim_start_frame:
                QMessageBox.warning(self, "경고", "끝 프레임은 시작 프레임보다 뒤에 있어야 합니다.")
                return
            self.trim_end_frame = current_frame
            self.trim_info_label.setText(f"자르기 구간: {self.trim_start_frame} ~ {self.trim_end_frame}")

    def save_trimmed_video(self):
        if not self.video_path or self.video_capture is None:
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "자른 영상 저장", "", "Video Files (*.mp4)", options=QFileDialog.DontUseNativeDialog)
        if not file_path:
            return
            
        if not file_path.lower().endswith('.mp4'):
            file_path += '.mp4'

        # UI 응답 방지 및 안내 표시
        self.save_trimmed_button.setText("저장 중...")
        self.save_trimmed_button.setEnabled(False)
        QApplication.processEvents()

        try:
            import tempfile
            import shutil

            fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            if fps == 0: fps = 30
            width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # OpenCV는 경로에 한글이 포함된 경우 저장이 실패하는 버그가 있어 임시 경로를 사용합니다.
            temp_file_path = os.path.join(tempfile.gettempdir(), "temp_export_video.mp4")

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out_video = cv2.VideoWriter(temp_file_path, fourcc, fps, (width, height))

            if not out_video.isOpened():
                raise Exception("비디오 코덱을 초기화할 수 없습니다. mp4v 코덱을 지원하지 않을 수 있습니다.")

            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, self.trim_start_frame)
            current_pos = self.trim_start_frame
            
            # 저장 진행률 표시용 변수
            total_export_frames = self.trim_end_frame - self.trim_start_frame + 1
            exported_count = 0

            while current_pos <= self.trim_end_frame:
                ret, frame = self.video_capture.read()
                if not ret:
                    break
                    
                # 원본 프레임만 자르기 저장
                out_video.write(frame)
                
                exported_count += 1
                if exported_count % 10 == 0 or exported_count == total_export_frames:
                    progress = int((exported_count / total_export_frames) * 100)
                    self.save_trimmed_button.setText(f"저장 중... {progress}%")
                    QApplication.processEvents()

                current_pos += 1
            
            out_video.release()
            
            # 임시로 저장된 파일을 최종 경로로 이동시킵니다.
            shutil.move(temp_file_path, file_path)

            # 궤적 데이터도 함께 맞춰서 자르고 저장
            trimmed_traj = {}
            for f_idx, pos in self.trajectory.items():
                if self.trim_start_frame <= f_idx <= self.trim_end_frame:
                    trimmed_traj[f_idx - self.trim_start_frame] = pos
            
            traj_file_path = os.path.splitext(file_path)[0] + "_trajectory.json"
            with open(traj_file_path, 'w', encoding='utf-8') as f:
                json.dump(trimmed_traj, f, indent=2)

            QMessageBox.information(self, "완료", f"영상이 성공적으로 저장되었습니다.\n{file_path}\n(시작된 프레임에 맞춘 궤적 데이터도 저장됨)")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"영상 저장 중 오류가 발생했습니다: {e}")
        finally:
            self.save_trimmed_button.setText("자른 원본 영상 저장하기")
            self.save_trimmed_button.setEnabled(True)
            
            # 완료 후 현재 위치로 복귀
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, self.trim_start_frame)
            ret, frame = self.video_capture.read()
            if ret:
                self.current_frame = frame.copy()
                self.display_frame(self.process_frame(self.current_frame))
                self.update_timeline()

    def export_anim_video(self):
        if not self.video_path or self.video_capture is None:
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "애니메이션 포함 영상 저장", "", "Video Files (*.mp4)", options=QFileDialog.DontUseNativeDialog)
        if not file_path:
            return
            
        if not file_path.lower().endswith('.mp4'):
            file_path += '.mp4'

        # UI 응답 방지 및 안내 표시
        self.export_anim_button.setText("저장 중...")
        self.export_anim_button.setEnabled(False)
        QApplication.processEvents()

        try:
            import tempfile
            import shutil

            fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            if fps == 0: fps = 30
            width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            temp_file_path = os.path.join(tempfile.gettempdir(), "temp_export_anim_video.mp4")

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out_video = cv2.VideoWriter(temp_file_path, fourcc, fps, (width, height))

            if not out_video.isOpened():
                raise Exception("비디오 코덱을 초기화할 수 없습니다. mp4v 코덱을 지원하지 않을 수 있습니다.")

            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, self.trim_start_frame)
            current_pos = self.trim_start_frame
            
            total_export_frames = self.trim_end_frame - self.trim_start_frame + 1
            exported_count = 0

            while current_pos <= self.trim_end_frame:
                ret, frame = self.video_capture.read()
                if not ret:
                    break
                    
                # 애니메이션 궤적을 렌더링하여 프레임 자체에 합성(Bake-in)
                processed_frame = self.process_frame(frame, export_mode=True)
                out_video.write(processed_frame)
                
                exported_count += 1
                if exported_count % 10 == 0 or exported_count == total_export_frames:
                    progress = int((exported_count / total_export_frames) * 100)
                    self.export_anim_button.setText(f"저장 중... {progress}%")
                    QApplication.processEvents()

                current_pos += 1
            
            out_video.release()
            shutil.move(temp_file_path, file_path)

            QMessageBox.information(self, "완료", f"애니메이션이 포함된 영상이 성공적으로 저장되었습니다.\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"영상 저장 중 오류가 발생했습니다: {e}")
        finally:
            self.export_anim_button.setText("애니메이션 포함 영상 저장하기")
            self.export_anim_button.setEnabled(True)
            
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, self.trim_start_frame)
            ret, frame = self.video_capture.read()
            if ret:
                self.current_frame = frame.copy()
                self.display_frame(self.process_frame(self.current_frame))
                self.update_timeline()

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
                if getattr(self, 'is_calibrating', False):
                    self.is_calibrating = False
                    self.calibration_points = []
                    QMessageBox.information(self, "취소", "영점 조절 모드가 취소되었습니다.")
                    if self.current_frame is not None:
                        self.display_frame(self.process_frame(self.current_frame))
                    return

                current_frame_idx = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                if current_frame_idx < 0:
                    current_frame_idx = 0
                if current_frame_idx in self.trajectory:
                    del self.trajectory[current_frame_idx]
                    self.trajectory_modified = True
                    self.update_traj_list()
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
