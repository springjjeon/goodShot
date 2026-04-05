import codecs

path = r"d:\dev\goodShot\main.py"
with codecs.open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1
old1 = '''        # 궤적 보기 옵션 체크박스
        self.show_trajectory_cb = QCheckBox("궤적 전체 보기")
        self.show_trajectory_cb.setChecked(True)
        self.show_trajectory_cb.setEnabled(False)

        # 궤적 예측 버튼 추가'''
new1 = '''        # 궤적 보기 옵션 체크박스
        self.show_trajectory_cb = QCheckBox("궤적 전체 보기")
        self.show_trajectory_cb.setChecked(False) # 기본값은 끄고 애니메이션을 켬
        self.show_trajectory_cb.setEnabled(False)

        # 애니메이션 모드 (Shot Tracer) 체크박스
        self.anim_mode_cb = QCheckBox("애니메이션 모드 (Shot Tracer)")
        self.anim_mode_cb.setChecked(True)
        self.anim_mode_cb.setEnabled(False)

        # 궤적 예측 버튼 추가'''
content = content.replace(old1, new1)

# 2
old2 = '''        self.control_layout.addWidget(self.load_button)
        self.control_layout.addWidget(self.play_button)
        self.control_layout.addWidget(self.show_trajectory_cb)
        self.control_layout.addWidget(self.predict_traj_button)'''
new2 = '''        self.control_layout.addWidget(self.load_button)
        self.control_layout.addWidget(self.play_button)
        self.control_layout.addWidget(self.show_trajectory_cb)
        self.control_layout.addWidget(self.anim_mode_cb)
        self.control_layout.addWidget(self.predict_traj_button)'''
content = content.replace(old2, new2)

# 3
old3 = '''        self.load_button.clicked.connect(self.load_video)
        self.play_button.clicked.connect(self.toggle_playback)
        self.show_trajectory_cb.toggled.connect(self.redraw_current_frame)
        self.predict_traj_button.clicked.connect(self.predict_trajectory)'''
new3 = '''        self.load_button.clicked.connect(self.load_video)
        self.play_button.clicked.connect(self.toggle_playback)
        self.show_trajectory_cb.toggled.connect(self.redraw_current_frame)
        self.anim_mode_cb.toggled.connect(self.redraw_current_frame)
        self.predict_traj_button.clicked.connect(self.predict_trajectory)'''
content = content.replace(old3, new3)

# 4
old4 = '''                self.play_button.setEnabled(True)
                self.show_trajectory_cb.setEnabled(True)
                self.predict_traj_button.setEnabled(True)'''
new4 = '''                self.play_button.setEnabled(True)
                self.show_trajectory_cb.setEnabled(True)
                self.anim_mode_cb.setEnabled(True)
                self.predict_traj_button.setEnabled(True)'''
content = content.replace(old4, new4)

# 5
old5 = '''    def process_frame(self, frame):
        """수동으로 입력된 좌표를 기반으로 마커와 궤적을 그립니다."""
        # 궤적 전체 보기가 꺼져있다면 원본 프레임 반환
        if not self.show_trajectory_cb.isChecked():
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
                    
        return display_frame'''

new5 = '''    def process_frame(self, frame):
        """수동으로 입력된 좌표를 기반으로 마커와 궤적을 그립니다."""
        is_show_all = self.show_trajectory_cb.isChecked()
        is_anim_mode = hasattr(self, 'anim_mode_cb') and self.anim_mode_cb.isChecked()
        
        # 궤적 전체 보기와 애니메이션 모드가 모두 꺼져있다면 원본 프레임 반환
        if not is_show_all and not is_anim_mode:
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
                        cv2.line(display_frame, points_to_draw[i-1], points_to_draw[i], (0, 200, 255), 4)
            else:
                try:
                    from scipy.interpolate import splprep, splev
                    pts = np.array(all_points, dtype=float)
                    
                    k = min(3, len(all_points) - 1)
                    smoothing_factor = len(all_points) * 10
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
                        if current_frame_idx >= all_sorted_frames[-1]:
                            u_max = 1.0
                        elif current_frame_idx > all_sorted_frames[0]:
                            for i in range(len(all_sorted_frames) - 1):
                                if all_sorted_frames[i] <= current_frame_idx < all_sorted_frames[i+1]:
                                    f1 = all_sorted_frames[i]
                                    f2 = all_sorted_frames[i+1]
                                    ratio = (current_frame_idx - f1) / (f2 - f1)
                                    u_max = u[i] + ratio * (u[i+1] - u[i])
                                    break
                                    
                        if u_max > 0.0:
                            num_points = max(10, int(300 * u_max))
                            u_anim = np.linspace(0, u_max, num_points)
                            x_anim, y_anim = splev(u_anim, tck)
                            anim_pts = np.column_stack((x_anim, y_anim))
                            anim_curve = np.int32(anim_pts).reshape((-1, 1, 2))
                            
                            # 멋진 트레이서 효과 (3겹 글로우 효과)
                            cv2.polylines(display_frame, [anim_curve], False, (0, 100, 255), 8) # 두꺼운 주황/빨강
                            cv2.polylines(display_frame, [anim_curve], False, (0, 200, 255), 4) # 노란색 중간
                            cv2.polylines(display_frame, [anim_curve], False, (255, 255, 255), 2) # 얇은 흰색 중심
                            
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
                            cv2.line(display_frame, points_to_draw[i-1], points_to_draw[i], (0, 200, 255), 4)
                    
        return display_frame'''

content = content.replace(old5, new5)

with codecs.open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied successfully.")