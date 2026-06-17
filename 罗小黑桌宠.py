# ...existing code...import sys
import os
import sys
import random
import logging
from PyQt5 import QtWidgets, QtGui, QtCore
from datetime import datetime
import gc  # 在文件顶部导入gc

def res_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # 打包后的资源路径
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境下的资源路径
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

# 配置日志

try:
    # 确保日志目录存在
    log_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_path = os.path.join(log_dir, 'deskpet.log')
    
    # 检查日志文件是否可写
    try:
        with open(log_path, 'a') as f:
            f.write('')  # 测试写入
    except IOError as e:
        log_path = os.path.join(os.path.expanduser('~'), 'deskpet.log')
    
    # 配置日志
    # 配置日志处理器
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # 移除所有现有处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    try:
        # 尝试文件日志
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        logger.info("日志系统初始化成功，使用文件日志")
    except Exception as e:
        # 回退到控制台日志
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
        logger.error(f"无法初始化文件日志: {str(e)}，已回退到控制台日志")
    logger = logging.getLogger(__name__)
    logger.info("程序启动，日志系统初始化成功")
    logger.info(f"日志文件路径: {log_path}")

except Exception as e:
    # 回退到控制台日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    logger = logging.getLogger(__name__)
    logger.error(f"无法初始化文件日志系统: {str(e)}，已回退到控制台日志")



class DeskPet(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()
        self.idle_gif_path = res_path(os.path.join("assets","LXHflower.gif"))
        self.scale_factor = 1.0
        self.collectibles = []
        self.reminders = []
        self.hunger_points = 100
        self.is_working = False
        self.is_eating = False
        self.is_playing_random_animation = False
        
        # 初始化所有定时器
        self.collectible_timer = QtCore.QTimer(self)
        self.collectible_check_timer = QtCore.QTimer(self)
        self.hunger_timer = QtCore.QTimer(self)
        self.eat_timer = QtCore.QTimer(self)
        self.countdown_timer = QtCore.QTimer(self)
        
        self.initUI()

    def initUI(self):
        # Mac专用透明设置
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.NoDropShadowWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        # Mac下需要设置合成属性
        if sys.platform == 'darwin':
            self.setAttribute(QtCore.Qt.WA_MacNoShadow)
            self.setAttribute(QtCore.Qt.WA_AlwaysStackOnTop)
        # 设置透明调色板
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, QtCore.Qt.transparent)
        self.setPalette(palette)
        self.setGeometry(500, 500, 120, 120)
        self.currentAction = self.startIdle
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.updateAnimation)
        self.changeDirectionTimer = QtCore.QTimer(self)
        self.changeDirectionTimer.timeout.connect(self.changeDirection)
        self.startIdle()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showMenu)
        self.setMouseTracking(True)
        self.dragging = False
        self.reminder_timer = QtCore.QTimer(self)
        self.reminder_timer.timeout.connect(self.check_reminders)
        self.reminder_timer.start(1000)  # 每秒检查一次提醒
        # 新增工作模式状态
        self.is_working = False
        
        # 随机动画定时器
        self.random_animation_timer = QtCore.QTimer(self)
        self.random_animation_timer.timeout.connect(self.play_random_animation)
        self.random_animation_timer.start(2220000)  # 37分钟触发一次

    def loadGif(self, path, size=None):
        try:
            # 将相对路径转换为绝对路径
            if not os.path.isabs(path):
                base_dir = os.path.dirname(os.path.abspath(__file__))
                path = os.path.join(base_dir, path)

            # 检查文件是否存在
            if not os.path.exists(path):
                raise FileNotFoundError(f"GIF file not found: {path}\nCurrent directory: {os.getcwd()}")

            # Mac下优化GIF显示
            if sys.platform == 'darwin':
                try:
                    self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
                    self.setStyleSheet("background: transparent; border: none;")
                    # 强制清除调色板底色
                    palette = self.palette()
                    palette.setColor(QtGui.QPalette.Window, QtCore.Qt.transparent)
                    self.setPalette(palette)
                except Exception as e:
                    logger.error(f"Mac透明设置失败: {str(e)}")

            # 停止并清理旧动画
            try:
                if hasattr(self, 'gif') and self.gif:
                    self.gif.stop()
                    self.setMovie(None)
                    self.gif.deleteLater()
                    self.gif = None
            except Exception as e:
                logger.error(f"Error cleaning old GIF: {str(e)}")

            # 加载新的GIF
            try:
                self.gif = QtGui.QMovie(path)
                if not self.gif.isValid():
                    raise ValueError(f"Invalid GIF file: {path}")
                
                # Mac下设置抗锯齿
                if sys.platform == 'darwin':
                    try:
                        self.gif.setScaledSize(QtCore.QSize(
                            int(self.gif.scaledSize().width() * 1.1),
                            int(self.gif.scaledSize().height() * 1.1)
                        ))
                        self.setStyleSheet("""
                            QLabel {
                                background: transparent;
                                image-rendering: -webkit-optimize-contrast;
                            }
                        """)
                    except Exception as e:
                        logger.error(f"Mac抗锯齿设置失败: {str(e)}")

                # 设置缓存模式以提高性能
                self.gif.setCacheMode(QtGui.QMovie.CacheAll)

                # 连接信号
                self.gif.frameChanged.connect(self._on_first_frame_loaded)

                # 启动动画
                self.gif.start()

                # 检查是否成功启动
                if self.gif.frameCount() < 1:
                    raise RuntimeError("Failed to start GIF animation: no frames loaded")

                logger.info(f"Successfully loaded GIF: {path} with {self.gif.frameCount()} frames")
                return self.gif
            except Exception as e:
                logger.error(f"GIF loading error: {str(e)}")
                if hasattr(self, 'gif') and self.gif:
                    self.gif.deleteLater()
                    self.gif = None
                raise

        except Exception as e:
            logger.error(f"Failed to load GIF {path}: {str(e)}", exc_info=True)
            try:
                QtWidgets.QMessageBox.warning(self, "错误",
                                            f"无法加载动画文件: {path}\n错误信息: {str(e)}")
            except:
                pass
            # 回退到默认状态
            self.startIdle()
            return None

    def _on_first_frame_loaded(self, frame_number):
        """处理GIF第一帧加载事件"""
        if frame_number == 0:
            # 始终用GIF的原始尺寸
            gif_size = self.gif.currentImage().size()
            w = int(gif_size.width() * self.scale_factor)
            h = int(gif_size.height() * self.scale_factor)
            scaled_size = QtCore.QSize(w, h)
            self.setFixedSize(scaled_size)
            self.gif.setScaledSize(scaled_size)
            self.setMovie(self.gif)
            # 断开信号，防止后续每一帧都缩放
            try:
                self.gif.frameChanged.disconnect(self._on_first_frame_loaded)
            except Exception:
                pass

    def showMenu(self, position):
        menu = QtWidgets.QMenu()
        # 调节大小子菜单
        size_menu = QtWidgets.QMenu("调节大小", menu)
        for percent in [50, 75, 100, 125, 150, 200]:
            action = size_menu.addAction(f"{percent}%")
            action.triggered.connect(lambda checked, p=percent: self.set_scale_factor(p / 100.0))
        menu.addMenu(size_menu)
        # 其余菜单项
        if self.is_working:
            menu.addAction("退出工作模式", self.exit_work_mode)
            menu.addAction("隐藏", self.minimizeWindow)
            menu.addAction("退出", self.close)
        elif self.is_eating:
            menu.addAction("退出吃饭模式", self.exit_eat_mode)
            menu.addAction("隐藏", self.minimizeWindow)
            menu.addAction("退出", self.close)
        elif self.currentAction == self.startIdle:
            menu.addAction("滚动", self.startWalk)
            menu.addAction("下落", self.startFall)
            menu.addAction("吃饭", lambda: self.enter_eat_mode())
            # 播放动图子菜单
            animation_menu = QtWidgets.QMenu("播放动图", menu)
            animation_menu.addAction("钓鱼", lambda: self.loadGif(res_path(os.path.join("assets","LXHfish.gif"))))
            animation_menu.addAction("滑雪", lambda: self.loadGif(res_path(os.path.join("assets","LXHski.gif"))))
            animation_menu.addAction("开心", lambda: self.loadGif(res_path(os.path.join("assets","LXHhappy.gif"))))
            animation_menu.addAction("玩耍", lambda: self.loadGif(res_path(os.path.join("assets","LXHplay2.gif"))))
            animation_menu.addAction("数钱", lambda: self.loadGif(res_path(os.path.join("assets","LXHmoney.gif"))))
            animation_menu.addAction("无聊", lambda: self.loadGif(res_path(os.path.join("assets","LXHbored.gif"))))
            animation_menu.addAction("弹吉他", lambda: self.loadGif(res_path(os.path.join("assets","LXHguitar.gif"))))
            animation_menu.addAction("大笑", lambda: self.loadGif(res_path(os.path.join("assets","LXHlaugh.gif"))))
            animation_menu.addAction("背对", lambda: self.loadGif(res_path(os.path.join("assets","LXHtail.gif"))))
            menu.addMenu(animation_menu)
            menu.addAction("更换待机动图", self.change_idle_gif)
            menu.addAction("查看饥饿值", lambda: self.show_speech_bubble(f"当前饥饿值：{self.hunger_points}"))
            menu.addAction("工作模式", self.enter_work_mode)
            menu.addAction("添加提醒", self.createReminderInput)
            menu.addAction("倒计时", self.createCountdownInput)
            menu.addAction("正计时", self.start_stopwatch)
            menu.addAction("隐藏", self.minimizeWindow)
            menu.addAction("退出", self.close)
        elif self.currentAction == self.startWalk:
            menu.addAction("停止", self.startIdle)
            menu.addAction("隐藏", self.minimizeWindow)
            menu.addAction("退出", self.close)
        elif self.currentAction == self.startFall:
            menu.addAction("停止", self.startIdle)
            menu.addAction("隐藏", self.minimizeWindow)
            menu.addAction("退出", self.close)
        menu.exec_(self.mapToGlobal(position))

    def change_idle_gif(self):
        """弹出文件选择框，用户选择新的待机动图"""
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setWindowTitle("选择新的待机动图")
        file_dialog.setNameFilter("GIF 动图 (*.gif)")
        if file_dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_file = file_dialog.selectedFiles()[0]
            if os.path.exists(selected_file):
                try:
                    # 释放旧的 GIF 资源，防止文件被占用
                    if hasattr(self, 'gif') and self.gif:
                        self.gif.stop()
                        self.setMovie(None)
                        self.gif.deleteLater()
                        self.gif = None
                        gc.collect()  # 强制垃圾回收，加速释放文件句柄

                    # 创建assets目录(如果不存在)
                    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
                    if not os.path.exists(assets_dir):
                        os.makedirs(assets_dir)
                    
                    # 复制文件到assets目录，使用临时文件名
                    filename = os.path.basename(selected_file)
                    temp_filename = f"temp_{filename}"
                    temp_path = os.path.join(assets_dir, temp_filename)
                    import shutil
                    shutil.copy2(selected_file, temp_path)

                    # 删除原待机动图（如果存在且不是刚选的文件）
                    idle_gif_full_path = os.path.join(assets_dir, filename)
                    if os.path.exists(idle_gif_full_path):
                        try:
                            os.remove(idle_gif_full_path)
                        except Exception as e:
                            logger.warning(f"删除旧待机动图失败: {str(e)}")

                    # 重命名临时文件为正式文件名
                    os.rename(temp_path, idle_gif_full_path)

                    # 使用相对路径
                    self.idle_gif_path = os.path.join("assets", filename)
                    self.startIdle()
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "错误", f"更换动图失败: {str(e)}")
            else:
                QtWidgets.QMessageBox.warning(self, "错误", "文件不存在！")

    def set_scale_factor(self, factor):
        """设置缩放比例并刷新当前动画和气泡"""
        self.scale_factor = factor
        # 如果是吃饭或工作模式，只调整大小，不切换动图
        if self.is_eating or self.is_working:
            if hasattr(self, 'gif') and self.gif:
                # 重新设置缩放尺寸
                gif_size = self.gif.currentImage().size()
                w = int(gif_size.width() * self.scale_factor)
                h = int(gif_size.height() * self.scale_factor)
                scaled_size = QtCore.QSize(w, h)
                self.setFixedSize(scaled_size)
                self.gif.setScaledSize(scaled_size)
                self.speech_bubble.adjustSize() if hasattr(self, 'speech_bubble') and self.speech_bubble else None
                self.update_bubble_position() if hasattr(self, 'speech_bubble') and self.speech_bubble else None
            return

        if self.currentAction:
            self.currentAction()
        # 更新气泡大小
        if hasattr(self, 'speech_bubble') and self.speech_bubble:
            font_size = int(30 * self.scale_factor)
            self.bubble_label.setStyleSheet(f"""
                background-color: rgba(255, 255, 255, 0.9);
                border: 1px solid #ccc;
                border-radius: {int(15 * self.scale_factor)}px;
                padding: {int(15 * self.scale_factor)}px;
                font-size: {font_size}px;
                color: #333;
            """)
            self.speech_bubble.adjustSize()
            self.update_bubble_position()

    def generate_collectible(self):
        """生成可拾取物品，确保位置合理"""
        if self.collectibles:  # 确保只有一个收集物
            return
            
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        size = int(130 * self.scale_factor)
        pet_rect = self.geometry()
        
        # 生成位置时避开角落和桌宠位置
        max_attempts = 10
        for _ in range(max_attempts):
            # 边缘留出100像素空间
            x = random.randint(100, screen.width() - size - 100)
            y = random.randint(100, screen.height() - size - 100)
            
            # 检查是否与桌宠重叠
            collectible_rect = QtCore.QRect(x, y, size, size)
            if not pet_rect.intersects(collectible_rect):
                break
        else:
            logger.warning("无法找到合适的收集物位置")
            return
            
        collectible = QtWidgets.QLabel()
        collectible.setParent(self.parent())
        try:
            movie = QtGui.QMovie(res_path(os.path.join("assets","LXHheixiu.gif")))
            collectible.setFixedSize(size, size)
            collectible.setWindowFlags(
                QtCore.Qt.FramelessWindowHint |
                QtCore.Qt.WindowStaysOnTopHint)
            collectible.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            movie.setScaledSize(QtCore.QSize(size, size))
            collectible.setMovie(movie)
            movie.start()
            collectible.move(x, y)
            collectible.show()
            self.collectibles.append(collectible)
            logger.info(f"生成收集物在位置({x},{y})")
        except Exception as e:
            logger.error(f"生成收集物失败: {str(e)}")

    # ...existing code...

    def startIdle(self):
        self.currentAction = self.startIdle
        self.gif = self.loadGif(self.idle_gif_path)
        self.moveSpeed = 0
        self.movingDirection = 0
        if self.changeDirectionTimer.isActive():
            self.changeDirectionTimer.stop()

    def startWalk(self):
        self.currentAction = self.startWalk
        self.movingDirection = -1 if random.random() < 0.5 else 1
        self.moveSpeed = 10
        self.timer.start(100)
        self.changeDirectionTimer.start(3000)
        # 根据移动方向加载不同的动画
        if self.movingDirection < 0:
            self.gif = self.loadGif(res_path(os.path.join("assets","LXHroll.gif")))
        else:
            self.gif = self.loadGif(res_path(os.path.join("assets","LXHroll1.gif")))

    def startLift(self):
        # 关闭气泡
        if hasattr(self, 'speech_bubble'):
            self.speech_bubble.close()
            del self.speech_bubble
        self.currentAction = self.startLift
        self.gif = self.loadGif(res_path(os.path.join("assets","LXHplay.gif")))
        self.moveSpeed = 0
        self.movingDirection = 0
        self.timer.start(100)

    def startFall(self):
        self.currentAction = self.startFall
        self.gif = self.loadGif(res_path(os.path.join("assets","LXHmiao.gif")))
        self.moveSpeed = 5
        self.movingDirection = 0
        self.stopOtherActions()
        self.timer.start(30)

    def startCollect(self, collectible):
        """开始拾取物品"""
        try:
            if not collectible or not collectible.isVisible():
                logger.warning("无效的收集物对象")
                self.startIdle()
                return

            self.currentAction = self.startCollect
            self.moveSpeed = 30
            self.collectible = collectible
            self.timer.start(50)  # 加快更新频率
            
            # 根据初始方向加载动画
            pet_rect = self.geometry()
            collectible_rect = collectible.geometry()
            dx = collectible_rect.x() - pet_rect.x()
            self.current_run_direction = 'left' if dx < 0 else 'right'
            
            logger.info(f"开始拾取物品，方向: {self.current_run_direction}")
            
            # 验证动画资源路径
            left_gif = res_path(os.path.join("assets","LXHrun.gif"))
            right_gif = res_path(os.path.join("assets","LXHrunright.gif"))
            logger.info(f"左跑动画路径: {left_gif}")
            logger.info(f"右跑动画路径: {right_gif}")
            
            if dx < 0:
                if not os.path.exists(left_gif):
                    raise FileNotFoundError(f"左跑动画不存在: {left_gif}")
                self.loadGif(left_gif)
            else:
                if not os.path.exists(right_gif):
                    raise FileNotFoundError(f"右跑动画不存在: {right_gif}")
                self.loadGif(right_gif)
                
        except Exception as e:
            logger.error(f"开始拾取失败: {str(e)}", exc_info=True)
            self.startIdle()

    def updateHunger(self):
        if self.hunger_points > 0:
            self.hunger_points -= 1
            if self.hunger_points < 0:
                self.hunger_points = 0

    def play_eat_animation(self):
        self.loadGif("LXHeat.gif")
        # 等待动画播放完成
        self.movie.finished.connect(self.on_eat_finished)

    def on_eat_finished(self):
        self.hunger_points += 1
        if self.hunger_points > 100:
            self.hunger_points = 100
        self.show_speech_bubble(f"当前饥饿值：{self.hunger_points}")
        # 断开连接，避免重复触发
        self.movie.finished.disconnect(self.on_eat_finished)

    def stopOtherActions(self):
        self.timer.stop()
        # 关闭气泡
        if hasattr(self, 'speech_bubble'):
            self.speech_bubble.close()
            del self.speech_bubble
        if self.currentAction == self.startWalk:
            self.changeDirectionTimer.stop()
            self.startIdle()
        elif self.currentAction == self.startLift:
            self.startIdle()
        elif self.currentAction == self.startFall:
            pass
        else:
            self.startIdle()
        # 重置互动状态
        # 重置所有互动状态
        self.is_fishing = False
        self.is_skiing = False
        self.is_happy = False
        self.is_playing_guitar = False  # 吉他
        self.is_playing = False  # 玩耍
        self.is_counting_money = False  # 数钱
        self.is_bored = False  # 无聊
        self.is_forbidden = False  # 禁止
        self.is_confused = False  # 疑惑

    def updateAnimation(self):
        if self.currentAction == self.startFall:
            self.fallPet()
        elif self.currentAction == self.startCollect:
            self.moveTowardsCollectible()
        else:
            self.movePet()

    def fallPet(self):
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        new_y = self.y() + self.moveSpeed
        if new_y > screen.height() - self.height() - 10:
            new_y = screen.height() - self.height() - 10
            self.timer.stop()
            self.startIdle()
        self.move(self.x(), new_y)

    def movePet(self):
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        new_x = self.x() + self.movingDirection * self.moveSpeed
        if new_x < 10:
            new_x = 10
            self.movingDirection *= -1
        elif new_x > screen.width() - self.width() - 10:
            new_x = screen.width() - self.width() - 10
            self.movingDirection *= -1
        self.move(new_x, self.y())

    def moveTowardsCollectible(self):
        if not hasattr(self, 'collectible') or self.collectible is None:
            self.startIdle()
            return

        pet_rect = self.geometry()
        collectible_rect = self.collectible.geometry()

        if pet_rect.intersects(collectible_rect):
            try:
                logger.info("成功拾取物品")
                self.collectible.deleteLater()
                if self.collectible in self.collectibles:
                    self.collectibles.remove(self.collectible)
                self.collectible = None
                self.startIdle()
                self.collectible_timer.start(30000)
                return
            except Exception as e:
                logger.error(f"拾取物品后清理失败: {str(e)}")
                self.startIdle()
                return

        pet_center = pet_rect.center()
        collectible_center = collectible_rect.center()

        dx = collectible_center.x() - pet_center.x()
        dy = collectible_center.y() - pet_center.y()

        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance > 0:
            move_x = int(dx / distance * self.moveSpeed)
            move_y = int(dy / distance * self.moveSpeed)

            new_x = self.x() + move_x
            new_y = self.y() + move_y

            screen = QtWidgets.QDesktopWidget().screenGeometry()
            if new_x < 0:
                new_x = 0
            elif new_x > screen.width() - self.width():
                new_x = screen.width() - self.width()

            if new_y < 0:
                new_y = 0
            elif new_y > screen.height() - self.height():
                new_y = screen.height() - self.height()

            self.move(new_x, new_y)

            # 仅在方向变化时切换动画
            current_direction = 'left' if dx < 0 else 'right'
            if current_direction != self.current_run_direction:
                self.current_run_direction = current_direction
                if dx < 0:
                    self.loadGif(res_path(os.path.join("assets","LXHrun.gif")))
                else:
                    self.loadGif(res_path(os.path.join("assets","LXHrunright.gif")))


    def enter_work_mode(self):
        """进入工作模式"""
        self.is_working = True
        self.key_press_count = 0  # 重置按键计数器
        self.stopOtherActions()
        
        # 暂停收集物功能
        self.collectible_timer.stop()
        self.collectible_check_timer.stop()
        
        # 清除现有收集物
        for collectible in self.collectibles:
            collectible.deleteLater()
        self.collectibles.clear()
        
        # 加载工作动画（所有平台都执行）
        try:
            gif_path = res_path(os.path.join("assets","LXHwork.gif"))
            logger.info(f"尝试加载工作动画: {gif_path}")
            if not os.path.exists(gif_path):
                raise FileNotFoundError(f"工作动画不存在: {gif_path}")
            self.loadGif(gif_path)
            self.show_speech_bubble("工作模式已启动\n按键次数: 0")
        except Exception as e:
            logger.error(f"加载工作动画失败: {str(e)}", exc_info=True)
            self.loadGif(self.idle_gif_path)
            self.show_speech_bubble("工作动画加载失败，已恢复默认状态")

        # 全平台键盘监听（必须放在方法内部！）
        try:
            from pynput import keyboard

            def on_press(key):
                try:
                    self.key_press_count += 1
                    self.show_speech_bubble(f"工作模式下已敲击键盘{self.key_press_count}次")
                except Exception as e:
                    logger.error(f"按键处理错误: {str(e)}")

            # 停止旧监听器
            if hasattr(self, 'listener') and self.listener:
                try:
                    self.listener.stop()
                except Exception:
                    pass

            self.listener = keyboard.Listener(on_press=on_press)
            self.listener.daemon = True
            self.listener.start()
        except ImportError:
            logger.error("pynput库未安装")
            self.show_speech_bubble("请安装pynput: pip install pynput")
            self.startIdle()
            return
        except Exception as e:
            logger.error(f"键盘监听初始化失败: {str(e)}")
            self.show_speech_bubble("键盘监听失败，请检查权限设置")
            self.startIdle()
            return

    def handle_global_key(self, key=None):
        """处理全局按键事件"""
        if self.is_working:
            self.key_press_count += 1
            try:
                # 每次按键都更新显示（按用户要求）
                self.show_speech_bubble(f"工作模式下已敲击键盘{self.key_press_count}次")
                # 每500次记录一次性能日志
                if self.key_press_count % 500 == 0:
                    logger.info(f"工作模式按键计数: {self.key_press_count}")
            except Exception as e:
                logger.error(f"处理按键事件失败: {str(e)}")

    def keyPressEvent(self, event):
        """窗口内键盘按键事件处理"""
        pass  # 现在由全局快捷键处理按键计数
        
    def exit_work_mode(self):
        """退出工作模式"""
        self.is_working = False
        # 恢复收集物功能
        self.collectible_timer.start(30000)
        self.collectible_check_timer.start(100)
        # 移除键盘监听器
        if hasattr(self, 'shortcut'):
            self.shortcut.deleteLater()
            del self.shortcut
        # 安全停止监听器
        if hasattr(self, 'listener'):
            try:
                if self.listener.is_alive():
                    self.listener.stop()
                self.listener = None
            except Exception as e:
                logger.error(f"停止键盘监听失败: {str(e)}")
        # 关闭气泡
        if hasattr(self, 'speech_bubble'):
            self.speech_bubble.close()
            del self.speech_bubble
        self.startIdle()

    def minimizeWindow(self):
        self.showMinimized()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            # 吃饭/工作模式下只允许拖动，不切换动图
            if self.is_eating or self.is_working:
                self.dragging = True
                self.drag_position = event.globalPos() - self.pos()
                event.accept()
                return

            # 非特殊模式下正常处理
            if hasattr(self, 'speech_bubble'):
                self.speech_bubble.close()
                del self.speech_bubble
            self.dragging = True
            self.drag_position = event.globalPos() - self.pos()
            self.prevAction = self.currentAction
            self.startLift()
            event.accept()

    def mouseMoveEvent(self, event):
        if QtCore.Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            # 移动时更新气泡位置
            if hasattr(self, 'speech_bubble'):
                self.update_bubble_position()
            event.accept()

        # 保持气泡显示直到动画结束

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = False
            # 吃饭/工作模式下不执行任何状态改变
            if self.is_eating or self.is_working:
                event.accept()
                return

            # 非特殊模式下正常处理
            if self.currentAction == self.startWalk:
                self.changeDirectionTimer.start()
            self.prevAction()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            # 吃饭/工作模式下不切换动图
            if self.is_eating or self.is_working:
                return
            self.startLift()

    def createReminderInput(self):
        self.reminder_input = QtWidgets.QInputDialog(self)
        self.reminder_input.setInputMode(QtWidgets.QInputDialog.TextInput)
        self.reminder_input.setWindowTitle("添加提醒")
        self.reminder_input.setLabelText("请输入提醒内容:")
        font = QtGui.QFont()
        font.setPointSize(12)
        self.reminder_input.setFont(font)
        if self.reminder_input.exec_() == QtWidgets.QDialog.Accepted:
            reminder_text = self.reminder_input.textValue()
            self.set_reminder(reminder_text)

    def set_reminder(self, reminder_text):
        time_dialog = QtWidgets.QTimeEdit(self)
        time_dialog.setWindowTitle("设置提醒时间")
        time_dialog.setCalendarPopup(True)
        font = QtGui.QFont()
        font.setPointSize(12)
        time_dialog.setFont(font)
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("设置提醒时间")
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(time_dialog)
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        dialog.setFont(font)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            reminder_time = time_dialog.time().toPyTime()
            current_time = datetime.now().time()
            if reminder_time < current_time:
                QtWidgets.QMessageBox.warning(self, "错误", "提醒时间不能早于当前时间！")
                return
            self.reminders.append((reminder_time, reminder_text))
            QtWidgets.QMessageBox.information(self, "成功", "提醒已设置！")

    def check_reminders(self):
        current_time = datetime.now().time()
        for reminder in self.reminders:
            reminder_time, reminder_text = reminder
            if current_time.hour == reminder_time.hour and current_time.minute == reminder_time.minute:
                self.showReminderDialog(reminder_text)
                self.reminders.remove(reminder)

    def showReminderDialog(self, reminder_text):
        font = QtGui.QFont()
        font.setPointSize(12)
        msg_box = QtWidgets.QMessageBox()
        msg_box.setWindowTitle("提醒")
        msg_box.setText(f"提醒: {reminder_text}")
        msg_box.setFont(font)
        msg_box.exec_()


    def check_collectibles(self):
        """检查并处理最近的收集物"""
        if self.is_working or self.is_eating or self.is_playing_random_animation:
            return

        try:
            if not self.collectibles or self.currentAction not in [self.startIdle, self.startWalk]:
                return

            pet_rect = self.geometry()
            nearest_collectible = None
            min_distance = float('inf')

            # 过滤掉无效的收集物
            self.collectibles = [c for c in self.collectibles if c and c.isVisible()]
            
            for collectible in self.collectibles:
                try:
                    collectible_rect = collectible.geometry()
                    if pet_rect.intersects(collectible_rect):
                        continue

                    dx = collectible_rect.x() - pet_rect.x()
                    dy = collectible_rect.y() - pet_rect.y()
                    distance = (dx ** 2 + dy ** 2) ** 0.5
                    
                    # 放宽距离限制(屏幕宽度的2倍以内)
                    if distance < min_distance and distance < pet_rect.width() * 20:
                        min_distance = distance
                        nearest_collectible = collectible

                except Exception as e:
                    logger.error(f"检查收集物时出错: {str(e)}")
                    continue

            if nearest_collectible:
                logger.info(f"发现可拾取物品，距离: {min_distance:.1f}px")
                if self.currentAction == self.startIdle:
                    self.startCollect(nearest_collectible)
                elif self.currentAction == self.startWalk:
                    self.stopOtherActions()
                    self.startCollect(nearest_collectible)
                    
        except Exception as e:
            logger.error(f"检查收集物失败: {str(e)}", exc_info=True)

    def createCountdownInput(self):
        self.countdown_dialog = QtWidgets.QDialog(self)
        self.countdown_dialog.setWindowTitle("设置倒计时")
        self.countdown_dialog.setModal(True)
        layout = QtWidgets.QVBoxLayout(self.countdown_dialog)

        hour_layout = QtWidgets.QHBoxLayout()
        hour_label = QtWidgets.QLabel("小时:", self.countdown_dialog)
        self.hour_spinbox = QtWidgets.QSpinBox(self.countdown_dialog)
        self.hour_spinbox.setRange(0, 24)
        hour_layout.addWidget(hour_label)
        hour_layout.addWidget(self.hour_spinbox)

        minute_layout = QtWidgets.QHBoxLayout()
        minute_label = QtWidgets.QLabel("分钟:", self.countdown_dialog)
        self.minute_spinbox = QtWidgets.QSpinBox(self.countdown_dialog)
        self.minute_spinbox.setRange(0, 59)
        minute_layout.addWidget(minute_label)
        minute_layout.addWidget(self.minute_spinbox)

        second_layout = QtWidgets.QHBoxLayout()
        second_label = QtWidgets.QLabel("秒数:", self.countdown_dialog)
        self.second_spinbox = QtWidgets.QSpinBox(self.countdown_dialog)
        self.second_spinbox.setRange(0, 59)
        second_layout.addWidget(second_label)
        second_layout.addWidget(self.second_spinbox)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
                                                self.countdown_dialog)
        button_box.accepted.connect(self.start_countdown)
        button_box.rejected.connect(self.countdown_dialog.reject)

        layout.addLayout(hour_layout)
        layout.addLayout(minute_layout)
        layout.addLayout(second_layout)
        layout.addWidget(button_box)

        font = QtGui.QFont()
        font.setPointSize(12)
        self.countdown_dialog.setFont(font)

        self.countdown_dialog.show()

    def start_countdown(self):
        hours = self.hour_spinbox.value()
        minutes = self.minute_spinbox.value()
        seconds = self.second_spinbox.value()
        total_seconds = hours * 3600 + minutes * 60 + seconds

        if total_seconds <= 0:
            QtWidgets.QMessageBox.warning(self, "错误", "倒计时时间必须大于0！")
            return

        self.countdown_time = total_seconds

        self.countdown_window = QtWidgets.QDialog(self)
        self.countdown_window.setWindowTitle("倒计时")
        self.countdown_window.setModal(False)
        layout = QtWidgets.QVBoxLayout(self.countdown_window)

        self.countdown_label = QtWidgets.QLabel()
        font = QtGui.QFont()
        font.setPointSize(24)
        self.countdown_label.setFont(font)
        layout.addWidget(self.countdown_label)

        self.update_countdown_display()
        self.countdown_window.show()

        # 启动倒计时定时器
        self.countdown_timer = QtCore.QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)  # 每秒更新一次

        self.countdown_dialog.accept()

    def start_stopwatch(self):
        """启动正计时"""
        self.stopwatch_time = 0
        self.is_paused = False
        self.stopwatch_window = QtWidgets.QDialog(self)
        self.stopwatch_window.setWindowTitle("正计时")
        layout = QtWidgets.QVBoxLayout(self.stopwatch_window)
        
        self.stopwatch_label = QtWidgets.QLabel("00:00:00")
        font = QtGui.QFont()
        font.setPointSize(24)
        self.stopwatch_label.setFont(font)
        layout.addWidget(self.stopwatch_label)
        
        button_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton("开始")
        self.pause_button = QtWidgets.QPushButton("暂停")
        self.stop_button = QtWidgets.QPushButton("停止")
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)

        self.start_button.clicked.connect(self._start_stopwatch_timer)
        self.pause_button.clicked.connect(self.pause_stopwatch)
        self.stop_button.clicked.connect(self.stop_stopwatch)
        
        self.pause_button.setEnabled(False)
        self.stopwatch_window.show()

    def _start_stopwatch_timer(self):
        self.stopwatch_timer = QtCore.QTimer(self)
        self.stopwatch_timer.timeout.connect(self.update_stopwatch)
        self.stopwatch_timer.start(1000)  # 每秒更新一次
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.is_paused = False

    def update_stopwatch(self):
        """正计时窗口刷新"""
        if not self.is_paused:
            self.stopwatch_time += 1
            hours = self.stopwatch_time // 3600
            minutes = (self.stopwatch_time % 3600) // 60
            seconds = self.stopwatch_time % 60
            self.stopwatch_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            QtCore.QCoreApplication.processEvents()

    def pause_stopwatch(self):
        """暂停正计时"""
        if hasattr(self, 'stopwatch_timer') and self.stopwatch_timer.isActive():
            self.is_paused = True
            self.stopwatch_timer.stop()
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            
    def resume_stopwatch(self):
        """继续正计时"""
        self.is_paused = False
        self._start_stopwatch_timer()
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)

    def stop_stopwatch(self):
        """停止正计时"""
        if hasattr(self, 'stopwatch_timer') and self.stopwatch_timer.isActive():
            self.stopwatch_timer.stop()
        if self.stopwatch_window:
            self.stopwatch_window.accept()
            self.stopwatch_window = None

    def update_countdown(self):
        """更新倒计时/正计时显示"""
        if self.countdown_time is not None:
            # 倒计时模式
            self.countdown_time -= 1
            if self.countdown_time <= 0:
                self.countdown_timer.stop()
                self.countdown_window.accept()
                self.show_countdown_finished_dialog()
            else:
                self.update_countdown_display()
        elif self.stopwatch_window:
            # 正计时模式
            self.stopwatch_time += 1
            hours = self.stopwatch_time // 3600
            minutes = (self.stopwatch_time % 3600) // 60
            seconds = self.stopwatch_time % 60
            self.stopwatch_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            # 强制刷新界面
            QtCore.QCoreApplication.processEvents()

    def update_countdown_display(self):
        if self.countdown_time is None:
            return

        hours = self.countdown_time // 3600
        minutes = (self.countdown_time % 3600) // 60
        seconds = self.countdown_time % 60
        self.countdown_label.setText(f"剩余时间: {hours} 小时 {minutes} 分钟 {seconds} 秒")

    def show_countdown_finished_dialog(self):
        font = QtGui.QFont()
        font.setPointSize(12)
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("倒计时完成")
        msg_box.setText("倒计时已完成！")
        msg_box.setFont(font)
        msg_box.exec_()

    def check_eat_time(self):
        current_time = datetime.now().time()
        eat_times = [datetime.strptime("08:00", "%H:%M").time(), datetime.strptime("12:00", "%H:%M").time(),
                     datetime.strptime("18:00", "%H:%M").time()]
        for eat_time in eat_times:
            if current_time.hour == eat_time.hour and current_time.minute == eat_time.minute:
                self.play_eat_animation()

    def show_speech_bubble(self, text):
        try:
            # 如果气泡不存在则创建
            if not hasattr(self, 'speech_bubble') or not self.speech_bubble:
                # 创建气泡对象
                self.speech_bubble = QtWidgets.QDialog(self)
                
                # 设置窗口属性
                self.speech_bubble.setWindowFlags(
                    QtCore.Qt.FramelessWindowHint |
                    QtCore.Qt.WindowStaysOnTopHint |
                    QtCore.Qt.Tool
                )
                self.speech_bubble.setAttribute(QtCore.Qt.WA_TranslucentBackground)
                self.speech_bubble.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)

                # 创建布局和标签
                self.bubble_layout = QtWidgets.QVBoxLayout(self.speech_bubble)
                self.bubble_label = QtWidgets.QLabel(self.speech_bubble)
                font_size = int(30 * self.scale_factor)
                padding = int(15 * self.scale_factor)
                radius = int(15 * self.scale_factor)
                self.bubble_label.setStyleSheet(f"""
                    background-color: rgba(255, 255, 255, 0.9);
                    border: 1px solid #ccc;
                    border-radius: {radius}px;
                    padding: {padding}px;
                    font-size: {font_size}px;
                    color: #333;
                """)
                self.bubble_layout.addWidget(self.bubble_label)
                self.bubble_layout.setContentsMargins(0, 0, 0, 0)
                
                # 调整大小并显示
                self.speech_bubble.adjustSize()
                self.update_bubble_position()
                self.speech_bubble.show()
            
            # 更新气泡内容
            self.bubble_label.setText(text)
            self.speech_bubble.adjustSize()
            self.update_bubble_position()
            
            # 记录性能日志
            if hasattr(self, 'key_press_count') and self.key_press_count % 500 == 0:
                logger.info(f"气泡更新次数: {self.key_press_count}")
                
        except Exception as e:
            logger.error(f"更新气泡显示失败: {str(e)}")

    def update_bubble_position(self):
        """更新气泡位置使其跟随桌宠"""
        if hasattr(self, 'speech_bubble') and self.speech_bubble:
            screen_pos = self.mapToGlobal(QtCore.QPoint(0, 0))
            # 考虑缩放比例调整位置
            offset = int(10 * self.scale_factor)
            bubble_x = screen_pos.x() + (self.width() - self.speech_bubble.width()) // 2
            bubble_y = screen_pos.y() - self.speech_bubble.height() - offset
            self.speech_bubble.move(bubble_x, bubble_y)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            # 吃饭/工作模式下只允许拖动，不切换动图
            if self.is_eating or self.is_working:
                self.dragging = True
                self.drag_position = event.globalPos() - self.pos()
                event.accept()
                return

            # 非特殊模式下正常处理
            if hasattr(self, 'speech_bubble'):
                self.speech_bubble.close()
                del self.speech_bubble
            self.dragging = True
            self.drag_position = event.globalPos() - self.pos()
            self.prevAction = self.currentAction
            self.startLift()
            event.accept()

    def mouseMoveEvent(self, event):
        if QtCore.Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            # 移动时更新气泡位置
            if hasattr(self, 'speech_bubble'):
                self.update_bubble_position()
            event.accept()

        # 保持气泡显示直到动画结束

    def enter_eat_mode(self):
        """进入吃饭模式"""
        try:
            self.is_eating = True
            self.stopOtherActions()
            # 停止随机动画定时器
            if self.random_animation_timer.isActive():
                self.random_animation_timer.stop()
            
            # 暂停收集物功能
            self.collectible_timer.stop()
            self.collectible_check_timer.stop()
            # 清除现有收集物
            for collectible in self.collectibles:
                collectible.deleteLater()
            self.collectibles.clear()
            
            # 加载吃饭动画
            gif_path = res_path(os.path.join("assets","LXHeat.gif"))
            if not os.path.exists(gif_path):
                raise FileNotFoundError(f"吃饭动画文件不存在: {gif_path}")
                
            self.loadGif(gif_path)
            
            # 初始化定时器
            if not hasattr(self, 'eat_animation_timer') or not self.eat_animation_timer:
                self.eat_animation_timer = QtCore.QTimer(self)
                self.eat_animation_timer.timeout.connect(self.increase_hunger)
            
            self.eat_animation_timer.start(1000)  # 每秒触发一次
                
            # 显示初始气泡
            self.show_speech_bubble("吃饭模式已启动\n饥饿值: {}".format(self.hunger_points))
            
        except Exception as e:
            logger.error(f"进入吃饭模式失败: {str(e)}")
            self.show_speech_bubble("吃饭模式启动失败")
            self.startIdle()

    def exit_eat_mode(self):
        """退出吃饭模式"""
        self.is_eating = False
        self.stop_eat_animation()
        # 恢复随机动画定时器
        if not self.random_animation_timer.isActive():
            self.random_animation_timer.start(180000)
        self.startIdle()

    def play_eat_animation(self):
        """兼容旧方法，直接进入吃饭模式"""
        self.enter_eat_mode()

    def increase_hunger(self):
        """每秒增加1点饥饿值"""
        self.hunger_points = min(100, self.hunger_points + 1)
        self.show_speech_bubble(f"好好吃饭\n饥饿值：{self.hunger_points}")

    def stop_eat_animation(self):
        if self.eat_animation_timer:
            self.eat_animation_timer.stop()
            self.eat_animation_timer = None
        # 关闭气泡
        if hasattr(self, 'speech_bubble'):
            self.speech_bubble.close()
            del self.speech_bubble
        
        # 恢复相关定时器
        if not self.hunger_timer.isActive():
            self.hunger_timer.start(120000)  # 2分钟减少1点
        if not self.collectible_timer.isActive() and not self.is_working:
            self.collectible_timer.start(30000)  # 30秒生成收集物
        if not self.collectible_check_timer.isActive() and not self.is_working:
            self.collectible_check_timer.start(100)  # 100ms检查收集物
            
        self.startIdle()

    def update_hunger(self):
        """每2分钟减少1点饥饿值"""
        self.hunger_points = max(0, self.hunger_points - 1)
        if self.hunger_points <= 20:
            self.show_speech_bubble(f"好饿啊...\n饥饿值：{self.hunger_points}")

    def play_random_animation(self):
        """随机播放一个动画"""
        if self.is_working or self.is_eating:
            return
            
        animations = [
            ("钓鱼", os.path.join("assets","LXHfish.gif")),
            ("滑雪", os.path.join("assets","LXHski.gif")),
            ("开心", os.path.join("assets","LXHhappy.gif")),
            ("玩耍", os.path.join("assets","LXHplay2.gif")),
            ("数钱", os.path.join("assets","LXHmoney.gif")),
            ("无聊", os.path.join("assets","LXHbored.gif")),
            ("弹吉他", os.path.join("assets","LXHguitar.gif")),
            ("大笑", os.path.join("assets","LXHlaugh.gif")),
            ("背对", os.path.join("assets","LXHtail.gif"))
        ]
        
        # 随机选择一个动画
        name, path = random.choice(animations)
        self.is_playing_random_animation = True
        self.loadGif(res_path(path))
        self.show_speech_bubble(f"播放动画: {name}")
        
        # 3分钟后恢复待机状态
        QtCore.QTimer.singleShot(180000, self.end_random_animation)
        
    def end_random_animation(self):
        """结束随机动画播放"""
        self.is_playing_random_animation = False
        self.startIdle()

        sys.exit(1)

    def changeDirection(self):
        """桌宠改变移动方向（占位实现）"""
        # 你可以根据需要实现方向切换逻辑
        if hasattr(self, 'movingDirection'):
            self.movingDirection *= -1

    def closeEvent(self, event):
        try:
            # 停止所有动画
            try:
                if hasattr(self, 'gif') and self.gif:
                    self.gif.stop()
                    self.gif.deleteLater()
                    self.gif = None
            except Exception as e:
                logger.error(f"Error stopping GIF: {str(e)}")

            # 停止所有定时器
            timers = [self.timer, self.changeDirectionTimer, self.reminder_timer,
                     self.collectible_timer, self.collectible_check_timer,
                     self.countdown_timer, self.eat_timer, self.hunger_timer]
            
            for timer in timers:
                try:
                    if timer and timer.isActive():
                        timer.stop()
                        timer.deleteLater()
                except Exception as e:
                    logger.error(f"Error stopping timer: {str(e)}")

            # 清理收集物
            try:
                while self.collectibles:
                    collectible = self.collectibles.pop()
                    if collectible:
                        try:
                            collectible.deleteLater()
                        except:
                            pass
            except Exception as e:
                logger.error(f"Error cleaning collectibles: {str(e)}")

            # 清理UI组件
            ui_components = [
                ('speech_bubble', '气泡'),
                ('countdown_window', '倒计时窗口'),
                ('reminder_input', '提醒输入框')
            ]
            
            for comp, name in ui_components:
                try:
                    if hasattr(self, comp):
                        getattr(self, comp).close()
                        getattr(self, comp).deleteLater()
                        delattr(self, comp)
                except Exception as e:
                    logger.error(f"Error cleaning {name}: {str(e)}")

            # 记录关闭事件
            logger.info("Desktop pet closed")

            # 确保所有事件处理完成
            try:
                QtCore.QCoreApplication.processEvents()
            except Exception:
                pass

            event.accept()

        except Exception as e:
            logger.error(f"Critical error during close: {str(e)}", exc_info=True)
            try:
                QtWidgets.QMessageBox.critical(None, "严重错误",
                    f"程序关闭时发生严重错误:\n{str(e)}\n请检查日志文件获取详细信息")
            except Exception as ex:
                logger.error(f"显示错误对话框失败: {str(ex)}")
if __name__ == "__main__":
    try:
        # 先初始化日志系统
        app = QtWidgets.QApplication(sys.argv)
        
        # 延迟创建主窗口
        def run_app():
            try:
                pet = DeskPet()
                pet.show()
            except Exception as e:
                logger.critical(f"创建主窗口失败: {str(e)}", exc_info=True)
                QtWidgets.QMessageBox.critical(
                    None,
                    "启动错误",
                    f"程序启动失败:\n{str(e)}\n详细信息请查看日志"
                )
                sys.exit(1)
        
        # 使用定时器延迟启动，确保事件循环就绪
        QtCore.QTimer.singleShot(100, run_app)
        sys.exit(app.exec_())
        
    except Exception as e:
        logging.critical(f"程序启动崩溃: {str(e)}", exc_info=True)
    def play_random_animation(self):
        """随机播放一个动画"""
        if self.is_working or self.is_eating:
            return
            
        animations = [
            ("钓鱼", os.path.join("assets","LXHfish.gif")),
            ("滑雪", os.path.join("assets","LXHski.gif")),
            ("开心", os.path.join("assets","LXHhappy.gif")),
            ("玩耍", os.path.join("assets","LXHplay2.gif")),
            ("数钱", os.path.join("assets","LXHmoney.gif")),
            ("无聊", os.path.join("assets","LXHbored.gif")),
            ("弹吉他", os.path.join("assets","LXHguitar.gif")),
            ("大笑", os.path.join("assets","LXHlaugh.gif")),
            ("背对", os.path.join("assets","LXHtail.gif"))
        ]
        
        # 随机选择一个动画
        name, path = random.choice(animations)
        self.is_playing_random_animation = True
        self.loadGif(res_path(path))
        self.show_speech_bubble(f"播放动画: {name}")
        
        # 3分钟后恢复待机状态
        QtCore.QTimer.singleShot(180000, self.end_random_animation)
        
    def end_random_animation(self):
        """结束随机动画播放"""
        self.is_playing_random_animation = False
        self.startIdle()

        sys.exit(1)