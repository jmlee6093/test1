from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
import time
import re
import ray

# ==========================================
# 사용자 설정 및 Ray 초기화
# ==========================================
LOTTECINEMA_ID = "dlwhdals6093@naver.com" 
LOTTECINEMA_PW = "jongmin0329!" 

# Ray 초기화 (사용자 환경에 맞춰 CPU 개수 조절)
ray.init(num_cpus=4, ignore_reinit_error=True, include_dashboard=False)

@ray.remote
class LotteCinemaActor:
    def __init__(self, actor_id, movie_index, region, theater, ticket_config, preferred_seat):
        self.actor_id = actor_id
        
        # 설정값 저장
        self.movie_index = movie_index
        self.region = region
        self.theater = theater
        self.ticket_config = ticket_config
        self.preferred_seat = preferred_seat
        self.target_count = sum(ticket_config.values())

        # 드라이버 설정
        options = Options()
        options.add_experimental_option("detach", True)
        prefs = {"profile.default_content_setting_values.geolocation": 2}
        options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=options)
        
        # 윈도우 배치 (Megabox 코드 방식 참고)
        x_pos = (actor_id % 2) * 960
        y_pos = 0
        self.driver.set_window_position(x_pos, y_pos)
        self.driver.set_window_size(960, 1000)

    def login(self):
        print(f"[{self.actor_id}번 Actor] 로그인 절차 진행")
        self.driver.get("https://www.lottecinema.co.kr/NLCHS/Member/login")
        try:
            id_input = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "userId")))
            id_input.send_keys(LOTTECINEMA_ID)

            pw_input = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "userPassword")))
            pw_input.send_keys(LOTTECINEMA_PW)
            
            login_btn = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn_login")))
            login_btn.click()
            time.sleep(4)
            return True
        except Exception as e:
            print(f"  -> [{self.actor_id}번] 로그인 실패: {e}")
            return False

    def select_movie_and_theater(self):
        print(f"[{self.actor_id}번 Actor] 영화 및 극장 선택 진행")
        self.driver.get("https://www.lottecinema.co.kr/NLCHS/Ticketing")
        time.sleep(3)

        try:
            # 영화 선택
            movie_list = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".movie_select_wrap.list.movieSelect ul li a"))
            )
            if len(movie_list) > self.movie_index:
                target_movie = movie_list[self.movie_index]
                self.driver.execute_script("arguments[0].click();", target_movie)
                time.sleep(1)

            # 지역 선택
            region_xpath = f"//div[contains(@class, 'cinema_select_wrap')]//li[contains(@class, 'depth1')]/a[contains(text(), '{self.region}')]"
            region_btn = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, region_xpath)))
            self.driver.execute_script("arguments[0].click();", region_btn)
            time.sleep(0.5)

            # 극장 선택
            theater_xpath = f"//li[contains(@class, 'depth1') and contains(@class, 'active')]//div[contains(@class, 'depth2')]//a[text()='{self.theater}']"
            theater_btn = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, theater_xpath)))
            self.driver.execute_script("arguments[0].click();", theater_btn)
            time.sleep(2)
            return True
        except Exception as e:
            print(f"  -> [{self.actor_id}번] 영화/극장 선택 실패: {e}")
            return False

    def analyze_seat_availability(self):
        if self.target_count == 0: return
        
        time.sleep(1)
        try:
            seat_container = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "seat_area")))
            container_width = seat_container.size['width']
            container_height = seat_container.size['height']
            all_seats = seat_container.find_elements(By.CSS_SELECTOR, "a.sel")
            
            seat_map = {}
            for seat in all_seats:
                if seat.get_attribute("seat-statuscode") != "0": continue
                
                style_str = seat.get_attribute("style") or ""
                left_match = re.search(r"left:\s*([\d.]+)px", style_str)
                top_match = re.search(r"top:\s*([\d.]+)px", style_str)
                
                if left_match and top_match and container_width > 0 and container_height > 0:
                    rel_x = float(left_match.group(1)) / container_width
                    rel_y = float(top_match.group(1)) / container_height
                    if not (self.preferred_seat["x_start"] <= rel_x <= self.preferred_seat["x_end"] and 
                            self.preferred_seat["y_start"] <= rel_y <= self.preferred_seat["y_end"]):
                        continue 
                
                seat_id = seat.get_attribute("data-seat")
                match = re.match(r"([A-Za-z]+)(\d+)", seat_id)
                if match:
                    row, col = match.group(1), int(match.group(2))
                    if row not in seat_map: seat_map[row] = []
                    seat_map[row].append(col)

            print(f"--- [{self.actor_id}번] 지정 범위 내 {self.target_count}명 연속 좌석 분석 ---")
            for row in sorted(seat_map.keys()):
                cols = sorted(seat_map[row])
                available = [f"{cols[i]}~{cols[i+self.target_count-1]}" for i in range(len(cols)-self.target_count+1) 
                             if cols[i+self.target_count-1] - cols[i] == self.target_count-1]
                if available: print(f" [{row} 열]: {', '.join(available)}")
        except:
            print(f"  -> [{self.actor_id}번] 좌석 분석 중 오류")

    def process_all_showtimes(self):
        try:
            time_xpath = "//a[@role='button' and .//dd[contains(@class, 'time')]]"
            time_elements = self.driver.find_elements(By.XPATH, time_xpath)
            valid_indices = [idx for idx, t in enumerate(time_elements) if t.is_displayed() and "disabled" not in (t.get_attribute("class") or "")]

            for i, btn_idx in enumerate(valid_indices):
                time.sleep(1.5)
                current_btns = self.driver.find_elements(By.XPATH, time_xpath)
                target_btn = current_btns[btn_idx]
                
                start_time = target_btn.find_element(By.CSS_SELECTOR, "dd.time strong").text
                print(f"[{self.actor_id}번] 상영 시간 {start_time} 분석 시작")
                
                self.driver.execute_script("arguments[0].click();", target_btn)
                time.sleep(1)
                
                try: Alert(self.driver).accept()
                except: pass

                # 팝업 닫기 및 단계 이동
                for btn in self.driver.find_elements(By.CSS_SELECTOR, "button.btn_close.btnCloseLayerMulti"):
                    if btn.is_displayed(): self.driver.execute_script("arguments[0].click();", btn)

                next_step_xpath = "//a[contains(@class, 'btn_col1') and contains(text(), '인원/좌석 선택')]"
                next_step_btn = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((By.XPATH, next_step_xpath)))
                self.driver.execute_script("arguments[0].click();", next_step_btn)
                time.sleep(2)

                # 인원 설정
                for t_type, count in self.ticket_config.items():
                    if count > 0:
                        plus_btn = self.driver.find_element(By.CSS_SELECTOR, f"li[data-peple='{t_type}'] button.btn_plus")
                        for _ in range(count):
                            self.driver.execute_script("arguments[0].click();", plus_btn)
                            time.sleep(0.3)

                self.analyze_seat_availability()
                
                # 다시 상영시간 선택으로 돌아가기
                step1_tab = self.driver.find_element(By.CSS_SELECTOR, "li.step01 > a")
                self.driver.execute_script("arguments[0].click();", step1_tab)
                time.sleep(1.5)

        except Exception as e:
            print(f"  -> [{self.actor_id}번] 순차 분석 중 오류: {e}")

    def run_full_process(self):
        if self.login():
            if self.select_movie_and_theater():
                self.process_all_showtimes()
        print(f"=== [{self.actor_id}번] 프로그램 종료 ===")
        self.driver.quit()

# ==========================================
# 실행 영역
# ==========================================
TICKET_CONFIG = {"성인": 2, "청소년": 0}
PREFERRED_SEAT = {"x_start": 0.5, "x_end": 0.75, "y_start": 0.5, "y_end": 0.75}

# 2개의 액터 생성 (각각 다른 영화 인덱스를 보거나 같은 영화를 분석 가능)
actors = [
    LotteCinemaActor.remote(i, 1, "서울", "건대입구", TICKET_CONFIG, PREFERRED_SEAT) 
    for i in range(2)
]

# 병렬 실행
results = [actor.run_full_process.remote() for actor in actors]
ray.get(results)
ray.shutdown()