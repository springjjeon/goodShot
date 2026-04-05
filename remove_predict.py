import codecs

path = r"d:\dev\goodShot\main.py"
with codecs.open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove predict_traj_button definition
old1 = '''        # 궤적 예측 버튼 추가
        self.predict_traj_button = QPushButton("궤적 예측하기")
        self.predict_traj_button.setEnabled(False)

'''
new1 = ""
if old1 in content:
    content = content.replace(old1, new1)

# 2. Remove predict_traj_button from layout
old2 = '''        self.control_layout.addWidget(self.anim_mode_cb)
        self.control_layout.addWidget(self.predict_traj_button)
        self.control_layout.addWidget(self.save_traj_button)'''
new2 = '''        self.control_layout.addWidget(self.anim_mode_cb)
        self.control_layout.addWidget(self.save_traj_button)'''
if old2 in content:
    content = content.replace(old2, new2)

# 3. Remove predict_traj_button signal connection
old3 = '''        self.anim_mode_cb.toggled.connect(self.redraw_current_frame)
        self.predict_traj_button.clicked.connect(self.predict_trajectory)
        self.save_traj_button.clicked.connect(self.export_trajectory)'''
new3 = '''        self.anim_mode_cb.toggled.connect(self.redraw_current_frame)
        self.save_traj_button.clicked.connect(self.export_trajectory)'''
if old3 in content:
    content = content.replace(old3, new3)

# 4. Remove predict_traj_button enabling
old4 = '''                self.anim_mode_cb.setEnabled(True)
                self.predict_traj_button.setEnabled(True)
                self.timeline_slider.setEnabled(True)'''
new4 = '''                self.anim_mode_cb.setEnabled(True)
                self.timeline_slider.setEnabled(True)'''
if old4 in content:
    content = content.replace(old4, new4)

# 5. Remove predict_trajectory method
old5 = '''    def predict_trajectory(self):
        """입력된 궤적 포인트들을 바탕으로, 시작 지점과 마지막 지점 사이의 비어있는 프레임 궤적을 예측(보간)합니다."""
        if not self.trajectory or len(self.trajectory) < 3:
            QMessageBox.warning(self, "경고", "궤적을 예측(보간)하려면 시작과 끝을 포함해 최소 3개 이상의 포인트가 필요합니다.")
            return

        if self.current_frame is None:
            return

        frame_h, frame_w = self.current_frame.shape[:2]

        # 프레임 인덱스(t)에 따른 x, y 좌표 데이터 준비
        sorted_frames = sorted(self.trajectory.keys())
        t_data = np.array(sorted_frames, dtype=float)
        points = np.array([self.trajectory[idx] for idx in sorted_frames], dtype=float)
        x_data = points[:, 0]
        y_data = points[:, 1]

        try:
            # 2차 다항식(포물선) 모델 피팅: x(t) = a*t^2 + b*t + c, y(t) = a*t^2 + b*t + c
            p_x = np.polyfit(t_data, x_data, 2)
            p_y = np.polyfit(t_data, y_data, 2)

            first_t = int(sorted_frames[0])
            last_t = int(sorted_frames[-1])
            predicted_count = 0

            # 시작 프레임부터 마지막 프레임 사이의 비어있는 구간을 예측하여 채움
            for t in range(first_t, last_t + 1):
                if t not in self.trajectory:
                    pred_x = int(np.polyval(p_x, t))
                    pred_y = int(np.polyval(p_y, t))

                    # 화면 경계에 맞게 보정
                    pred_x = max(0, min(frame_w - 1, pred_x))
                    pred_y = max(0, min(frame_h - 1, pred_y))
                    
                    self.trajectory[t] = (pred_x, pred_y)
                    predicted_count += 1

            if predicted_count > 0:
                self.trajectory_modified = True
                self.update_traj_list()
                self.auto_save_trajectory()
                self.redraw_current_frame()
                QMessageBox.information(self, "예측 완료", f"처음과 마지막 지점 사이의 비어있는 {predicted_count}개 프레임에 대한 궤적을 완성했습니다.")
            else:
                QMessageBox.information(self, "알림", "시작과 마지막 프레임 사이의 모든 궤적이 이미 채워져 있습니다.")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"궤적 예측 중 오류가 발생했습니다: {e}")

'''
new5 = ""
if old5 in content:
    content = content.replace(old5, new5)

with codecs.open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Removed predict trajectory button and logic.")