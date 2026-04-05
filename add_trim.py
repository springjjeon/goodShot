import codecs
import re

path = r"d:\dev\goodShot\main.py"
with codecs.open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add buttons
old1 = '''        # 저장 및 불러오기 버튼 (외부용)
        self.save_traj_button = QPushButton("궤적 내보내기")
        self.save_traj_button.setEnabled(False)
        self.load_traj_button = QPushButton("궤적 가져오기")
        self.load_traj_button.setEnabled(False)'''

new1 = '''        # 저장 및 불러오기 버튼 (외부용)
        self.save_traj_button = QPushButton("궤적 내보내기")
        self.save_traj_button.setEnabled(False)
        self.load_traj_button = QPushButton("궤적 가져오기")
        self.load_traj_button.setEnabled(False)
        
        # 영상 자르기 버튼
        self.trim_start_button = QPushButton("현재 프레임을 시작점으로 (In)")
        self.trim_start_button.setEnabled(False)
        self.trim_end_button = QPushButton("현재 프레임을 끝점으로 (Out)")
        self.trim_end_button.setEnabled(False)
        self.save_trimmed_button = QPushButton("자른 영상 저장하기")
        self.save_trimmed_button.setEnabled(False)
        self.trim_info_label = QLabel("자르기 구간: 전체")
        self.trim_info_label.setAlignment(Qt.AlignCenter)
        self.trim_info_label.setStyleSheet("color: #555; margin-top: 10px;")'''
content = content.replace(old1, new1)

# 2. Add to layout
old2 = '''        self.control_layout.addWidget(self.save_traj_button)
        self.control_layout.addWidget(self.load_traj_button)

        # 궤적 목록 리스트 추가'''
new2 = '''        self.control_layout.addWidget(self.save_traj_button)
        self.control_layout.addWidget(self.load_traj_button)
        
        # 자르기 관련 버튼 추가
        self.control_layout.addWidget(self.trim_start_button)
        self.control_layout.addWidget(self.trim_end_button)
        self.control_layout.addWidget(self.trim_info_label)
        self.control_layout.addWidget(self.save_trimmed_button)

        # 궤적 목록 리스트 추가'''
content = content.replace(old2, new2)

# 3. Instance variables
old3 = '''        self.trajectory = {}       # 프레임 인덱스를 키로 가지는 궤적 좌표 딕셔너리
        self.trajectory_modified = False  # 궤적 수정 여부 플래그
        
        # Connect signals'''
new3 = '''        self.trajectory = {}       # 프레임 인덱스를 키로 가지는 궤적 좌표 딕셔너리
        self.trajectory_modified = False  # 궤적 수정 여부 플래그
        
        self.trim_start_frame = 0
        self.trim_end_frame = -1
        
        # Connect signals'''
content = content.replace(old3, new3)

# 4. Connect signals
old4 = '''        self.delete_traj_button.clicked.connect(self.delete_selected_trajectory)

        self.setFocusPolicy(Qt.StrongFocus)'''
new4 = '''        self.delete_traj_button.clicked.connect(self.delete_selected_trajectory)
        self.trim_start_button.clicked.connect(self.set_trim_start)
        self.trim_end_button.clicked.connect(self.set_trim_end)
        self.save_trimmed_button.clicked.connect(self.save_trimmed_video)

        self.setFocusPolicy(Qt.StrongFocus)'''
content = content.replace(old4, new4)

# 5. Enable buttons on load_video
old5 = '''                self.timeline_slider.setEnabled(True)
                self.save_traj_button.setEnabled(True)
                self.load_traj_button.setEnabled(True)
                self.delete_traj_button.setEnabled(True)
                self.is_playing = False'''
new5 = '''                self.timeline_slider.setEnabled(True)
                self.save_traj_button.setEnabled(True)
                self.load_traj_button.setEnabled(True)
                self.delete_traj_button.setEnabled(True)
                
                self.trim_start_button.setEnabled(True)
                self.trim_end_button.setEnabled(True)
                self.save_trimmed_button.setEnabled(True)
                
                total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                self.trim_start_frame = 0
                self.trim_end_frame = max(0, total_frames - 1)
                self.trim_info_label.setText(f"자르기 구간: {self.trim_start_frame} ~ {self.trim_end_frame}")
                
                self.is_playing = False'''
content = content.replace(old5, new5)

# 6. Add trimming methods before next_frame
old6 = '''    def next_frame(self):'''
new6 = '''    def set_trim_start(self):
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
            
        # UI 응답 방지 및 안내 표시
        self.save_trimmed_button.setText("저장 중...")
        self.save_trimmed_button.setEnabled(False)
        QApplication.processEvents()

        try:
            fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            if fps == 0: fps = 30
            width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out_video = cv2.VideoWriter(file_path, fourcc, fps, (width, height))

            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, self.trim_start_frame)
            current_pos = self.trim_start_frame
            
            while current_pos <= self.trim_end_frame:
                ret, frame = self.video_capture.read()
                if not ret:
                    break
                    
                # 궤적 애니메이션이 켜져있다면, 인코딩된 프레임 자체에 궤적을 렌더링해서 저장할지 
                # (여기서는 원본 프레임만 저장하고 데이터는 JSON으로 분리 저장하는 방식을 택함)
                out_video.write(frame)
                current_pos += 1
            
            out_video.release()
            
            # 궤적 데이터도 함께 맞춰서 자르고 저장
            trimmed_traj = {}
            for f_idx, pos in self.trajectory.items():
                if self.trim_start_frame <= f_idx <= self.trim_end_frame:
                    trimmed_traj[f_idx - self.trim_start_frame] = pos
            
            traj_file_path = os.path.splitext(file_path)[0] + "_trajectory.json"
            with open(traj_file_path, 'w') as f:
                json.dump(trimmed_traj, f, indent=2)

            QMessageBox.information(self, "완료", f"영상이 성공적으로 저장되었습니다.\\n{file_path}\\n(시작된 프레임에 맞춘 궤적 데이터도 저장됨)")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"영상 저장 중 오류가 발생했습니다: {e}")
        finally:
            self.save_trimmed_button.setText("자른 영상 저장하기")
            self.save_trimmed_button.setEnabled(True)
            
            # 완료 후 현재 위치로 복귀
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, self.trim_start_frame)
            ret, frame = self.video_capture.read()
            if ret:
                self.current_frame = frame.copy()
                self.display_frame(self.process_frame(self.current_frame))
                self.update_timeline()

    def next_frame(self):'''
content = content.replace(old6, new6)

with codecs.open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Trim video functionality added.")