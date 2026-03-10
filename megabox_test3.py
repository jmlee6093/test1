# 크롤링 테스트
# (01.12 수정사항) prefs 변수 만들어 위치 정보 권한 강제로 차단하는 코드 만들었습니다. 제 환경 문제 때문에 만든거니 종민님 테스트 환경에서는 필요할때 쓰면 될거예요.
# ㄴ 참고한 링크 - https://velog.io/@sangyeon217/mocking-geolocation
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import ray
import time
import re
import random

# 메가박스 계정 정보 입력
MEGABOX_ID = "jmlee6093"  
MEGABOX_PW = "jongmin0329!" 

ray.init(num_cpus = 4, ignore_reinit_error=True, include_dashboard = False)
  
@ray.remote
class MegaboxActor:
    def __init__(self, actor_id):
        self.actor_id = actor_id
        
        time.sleep(self.actor_id*2)
        
        self.mbx_id = MEGABOX_ID
        self.mbx_pw = MEGABOX_PW

        options = Options()
        options.add_experimental_option("detach", True)
        
        # 위치 정보 권한 강제 차단 설정
        # geolocation 값: 1(허용), 2(차단) -> 2로 설정하여 위치 요청 거부
        prefs = {"profile.default_content_setting_values.geolocation": 2}
        options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(options=options)
        
        x_pos = (actor_id % 2) * 960
        y_pos = 0
        self.driver.set_window_position(x_pos, y_pos)
        self.driver.set_window_size(960, 1000)

        self.login()

    def login(self):
        # 메가박스 접속
        url = "https://www.megabox.co.kr/"
        self.driver.get(url)
        
        # 1. 로그인 띄우기
        try:
            login_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "로그인"))
            )
            login_link.click()
        except:
            self.driver.find_element(By.CSS_SELECTOR, ".link-login").click()
        time.sleep(1)
        
        # 2. 아이디 입력 (메가박스 ID 태그는 ibxLoginId)
        id_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "ibxLoginId"))
        )
        id_input.click()
        id_input.clear()
        id_input.send_keys(self.mbx_id)
        time.sleep(1)
        
        # 3. 비밀번호 입력 (메가박스 PW 태그는 ibxLoginPwd)
        pw_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "ibxLoginPwd"))
        )
        pw_input.click()
        pw_input.clear()
        pw_input.send_keys(self.mbx_pw)
        time.sleep(1)
        
        # 4. 로그인 버튼 클릭
        login_submit_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "btnLogin"))
        )
        login_submit_btn.click()
        time.sleep(3)
        
    def prepare_booking(self, movie_index):
        self.driver.get("https://www.megabox.co.kr/booking")
        time.sleep(3)
        
        if not self.select_movie(movie_index):
            print("영화 버튼을 찾지 못했습니다.")
            return
        
        try:
            WebDriverWait(self.driver,10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., '서울')]"))
            )
            self.find_element_simple("//button[contains(., '서울')]", "서울")
            time.sleep(0.5)
            if not self.find_element_simple("//button[contains(., '강남')]", "강남"):
                print("강남 지점 없음. 종료.")
                return
        except:
            print("서울 지역 버튼 못 찾음. 종료.")
            return
        time.sleep(2)
        
        if self.select_time_by_attribute():
            
            self.close_popups()
            for _ in range(5):
                if self.close_last_popup_smart():
                    break
                else:
                    print(".", end="", flush=True)
                    time.sleep(1.5)
        else:
            print("시간 선택 실패")
            
        TICKET_CONFIG = {"성인": 2, "경로": 0, "우대": 0}
        select_success = self.select_ticket_count(TICKET_CONFIG)

        if select_success:
            time.sleep(1)
            TARGET_COUNT = sum(TICKET_CONFIG.values())
            self.analyze_seat_availability(TARGET_COUNT)
        else:
            print(f"{self.actor_id}번 인원 선택 실패")
            
        print(f"{self.actor_id}번 모든 분석이 완료되었습니다.")    
    
    def select_movie(self, movie_index):
        try:
            movie_btn = self.find_nth_element_smart(
                By.CSS_SELECTOR, "button[movie-nm]", movie_index, 3
                )
        
            if movie_btn:
                movie_name = movie_btn.get_attribute("movie-nm")
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", movie_btn)
                return True
            return False
        except Exception as e:
            print("오류: {e}")
            return False
    time.sleep(1)
    
    def select_time_by_attribute(self):
        for i in range(10):
            try:
                times = self.driver.find_elements(By.CSS_SELECTOR, "button[play-start-time]")
                
                valid_times = [
                    t for t in times if "disabled" not in t.get_attribute("class")
                ]
                
                if len(valid_times) > 0:
                    idx = self.actor_id if self.actor_id < len(valid_times) else 0
                    target = valid_times[idx]
                    
                    start_time = target.get_attribute("play-start-time")
                    formatted_time = f"{start_time[:2]}:{start_time[2:]}"
                    
                    print(
                    f"  -> 선택할 시간: {formatted_time} (잔여 {target.get_attribute('rest-seat-cnt')}석)"
                )
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", target)
                    time.sleep(0.5)
                    self.driver.execute_script("arguments[0].click();", target)
                    return True
                
            except Exception as e:
                print(f"[{self.actor_id}번] 8번 절차 중 오류: {e}")
                
            time.sleep(1)
        return False
    
    def select_ticket_count(self, ticket_config):
        ticket_titles = {
            "성인": "성인 좌석 선택 증가",
            "경로": "경로 좌석 선택 증가",
            "우대": "우대 좌석 선택 증가",
        }
        
        try:
            for ticket_type, count in ticket_config.items():
                if count == 0: continue
                
                print(f"{self.actor_id}번 '{ticket_type}' {count}명 선택 시도 중...")
                target_title = ticket_titles[ticket_type]
                selector = f"button.up[title='{target_title}']"
                
                btn = self.find_nth_element_smart(By.CSS_SELECTOR, selector, 0, 3)
                
                if btn:
                    for _ in range(count):
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
                else:
                    return False
            return True
                
        except Exception as e:
            print(f"[{self.actor_id}번] 10번(인원 설정) 실패: {e}")
            return False
        
    def analyze_seat_availability(self, required_seats):
        if required_seats == 0:
            print(f"{self.actor_id}번 절차 불가능 (예매인원 0명 선택됨)")
            return
        
        try:
            self.driver.switch_to.default_content()
            seat_frame = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "frameBokdMSeat"))
            )
            self.driver.switch_to.frame(seat_frame)
        except:
            return
        
        time.sleep(2)
        
        try:
            seat_container = self.driver.find_element(By.CLASS_NAME, "seat-layout")
            all_seats = seat_container.find_elements(By.TAG_NAME, "button")
            
            seat_map = {}

            for seat in all_seats:
                cls = seat.get_attribute("class")
                seat_title = seat.get_attribute("title")
                
                if "finish" in cls or "impossible" in cls or "dim" in cls:
                    continue
                
                # 메가박스에서 예매 불가능한 장애인석/휠체어석 제외
                check_text = seat_title if seat_title else seat.text
                
                if "장애인" in check_text or "휠체어" in check_text:
                    continue

                style_str = seat.get_attribute("style")
                if style_str:
                    coords = re.findall(r"\d+", style_str)
                    
                    if len(coords) >= 3:
                        left = int(coords[0])
                        top = int(coords[1])
                        width = int(coords[2])
                        height = 18
                        total_width = 763
                        total_height = 150
                        
                        center_x = (left + (width / 2)) / total_width
                        center_y = (top + (height/ 2)) / total_height
                    else:
                        continue
                else:
                    continue
                
                preferred_seat = {
                    "x_start": 0.3,
                    "x_end": 0.5,
                    "y_start": 0.3,
                    "y_end": 0.5,
                }
                
                if not (
                    preferred_seat["x_start"] <= center_x <= preferred_seat["x_end"]
                    and preferred_seat["y_start"] <= center_y <= preferred_seat["y_end"]
                ):
                    continue

                match = re.search(r"([A-Za-z]+)\s*(\d+)", check_text)
                if match:
                    row = match.group(1)
                    col = int(match.group(2))
                    
                    if row not in seat_map:
                        seat_map[row] = []
                    seat_map[row].append(col)
                    
            sorted_rows = sorted(seat_map.keys())
                    
            print(f"--- {self.actor_id}번 필터링 및 정렬된 좌석 목록 ---")
            
            for row in sorted_rows:
                sorted_cols = sorted(seat_map[row])
            
            for col in sorted_cols:
                seat_name = f"{row}{col}"
                print(seat_name)
                
            total_seats = sum(len(cols) for cols in seat_map.values())
            print(f"------------------------------")
            print(f"총 추출된 좌석 수: {total_seats}개")

        except Exception as e:
            print(f"{self.actor_id}번 좌석 분석 실패: {e}")
            
    def find_nth_element_smart(self, by, value, index, timeout):
        
        def try_find_nth(idx, t_out):
            try:
                WebDriverWait(self.driver, t_out).until(
                    EC.presence_of_all_elements_located((by, value))
                )
                elements = self.driver.find_elements(by, value)
                if len(elements) > idx:
                    target = elements[idx]
                    return target
                return None
            except:
                return None
        
        self.driver.switch_to.default_content()
        result = try_find_nth(index, timeout)
        if result:
            return result
        
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        for i, frame in enumerate(iframes):
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame(frame)
                
                result = try_find_nth(index, 1)
                if result:
                    return result
            except:
                continue
        self.driver.switch_to.default_content()
        return None
    
    def find_element_simple(self, xpath, desc):
        try:
            el = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            self.driver.execute_script("arguments[0].click();", el)
            return True
        except:
            el = self.find_nth_element_smart(By.XPATH, xpath, 0, desc)
            if el:
                self.driver.execute_script("arguments[0].click();", el)
                return True
        return False
    
    def close_popups(self):
        for i in range(3):
            try:
                time.sleep(1)
                popup_btns = self.driver.find_elements(By.CSS_SELECTOR, "button.button.purple.confirm")
                visible_btns = [btn for btn in popup_btns if btn.is_displayed()]
                
                if visible_btns:
                    self.driver.execute_script("arguments[0].click();", visible_btns[0])
                    time.sleep(1)
                else:
                    break
            except:
                break
    
    def close_last_popup_smart(self):
        target_selector = "button.button.purple.close-layer"
        
        def try_close():
            try:
                btns = self.driver.find_elements(By.CSS_SELECTOR, target_selector)
                visible_btns = [b for b in btns if b.is_displayed()]
                if visible_btns:
                    self.driver.execute_script("arguments[0].click();", visible_btns[0])
                    time.sleep(1)
                    return True
            except:
                pass
            return False
        
        self.driver.switch_to.default_content()
        if try_close(): return True
        
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        for i, frame in enumerate(iframes):
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame(frame)
                if try_close():
                    return True
            except:
                continue
            
        self.driver.switch_to.default_content()
        return False
            
    def close_browser(self):
        try:
            self.driver.quit()
        except Exception as e:
            print("브라우저 종료 오류: {e}")
            
    def __del__(self):
        try:
            self.driver.quit()
        except:
            pass
 
# 2개의 액터 생성
actors = []
for i in range(2):
    actors.append(MegaboxActor.remote(i))
    time.sleep(random.uniform(2, 3))
    
TARGET_MOVIE_INDEX = 0

results = [actor.prepare_booking.remote(TARGET_MOVIE_INDEX) for actor in actors]
ray.get(results)

exit_calls = [actor.close_browser.remote() for actor in actors]
ray.get(exit_calls)

ray.shutdown()
