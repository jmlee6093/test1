# 롯데시네마 크롤링 (1.0.1과의 차이점 -> 선택한 영화,극장의 모든 예매 시간대(예매 버튼) 클릭하도록 순회)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
import time
import re

# ==========================================
# 사용자 설정 영역
# ==========================================
LOTTECINEMA_ID = "dlwhdals6093@naver.com" 
LOTTECINEMA_PW = "jongmin0329!" 

TARGET_MOVIE_INDEX = 1      # n번째 영화 (인덱스 1이면 2번째 영화)
TARGET_REGION = "서울"        # 지역 선택
TARGET_THEATER = "건대입구"    # 극장 선택

# 예매 인원 설정 (이 수치 조정을 통해 터미널에 출력되는 좌석 범위가 필터링해요)
TICKET_CONFIG = {
    "성인": 2,  
    "청소년": 0 
}

PREFERRED_SEAT = {
    "x_start": 0.5, 
    "x_end": 0.75, 
    "y_start": 0.5, 
    "y_end": 0.75
}
# ==========================================

options = Options()
options.add_experimental_option("detach", True)

# 위치 정보 권한 강제 차단 설정 (geolocation 값: 1(허용), 2(차단))
prefs = {
    "profile.default_content_setting_values.geolocation": 2
}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(options=options)
driver.maximize_window()

# 1~4. 로그인 띄우기 및 진행
print("[롯데시네마 접속 및 로그인 절차 진행]")
url = "https://www.lottecinema.co.kr/NLCHS/Member/login"
driver.get(url)

try:
    id_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "userId")))
    id_input.click()
    id_input.clear()
    id_input.send_keys(LOTTECINEMA_ID)

    pw_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "userPassword")))
    pw_input.click()
    pw_input.clear()
    pw_input.send_keys(LOTTECINEMA_PW)
    time.sleep(1)

    login_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn_login")))
    login_btn.click()
    time.sleep(4)
except Exception as e:
    print(f"로그인 실패: {e}")


# 5. 예매 페이지 이동
print("[5번(예매 페이지 이동)절차 진행]")
driver.get("https://www.lottecinema.co.kr/NLCHS/Ticketing")
time.sleep(3) 


# 6. 영화 선택
print("[6번(영화선택)절차 진행]")
try:
    movie_list = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".movie_select_wrap.list.movieSelect ul li a"))
    )
    
    if len(movie_list) > TARGET_MOVIE_INDEX:
        target_movie = movie_list[TARGET_MOVIE_INDEX]
        movie_title = target_movie.find_element(By.CSS_SELECTOR, "strong.tit").text
        print(f"  -> 선택한 영화: {movie_title}")
        
        driver.execute_script("arguments[0].click();", target_movie)
        time.sleep(1)
except Exception as e:
    print(f"  -> 영화 선택 실패: {e}")


# 7. 극장 선택
print("[7번(극장 선택)절차 진행]")
try:
    region_xpath = f"//div[contains(@class, 'cinema_select_wrap')]//li[contains(@class, 'depth1')]/a[contains(text(), '{TARGET_REGION}')]"
    region_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, region_xpath)))
    driver.execute_script("arguments[0].click();", region_btn)
    time.sleep(0.5)

    theater_xpath = f"//li[contains(@class, 'depth1') and contains(@class, 'active')]//div[contains(@class, 'depth2')]//a[text()='{TARGET_THEATER}']"
    theater_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, theater_xpath)))
    driver.execute_script("arguments[0].click();", theater_btn)
    print(f"  -> 극장 선택 완료: {TARGET_REGION} - {TARGET_THEATER}")
    time.sleep(2)
except Exception as e:
    print(f"  -> 극장 선택 실패: {e}")


# 좌석 분석 함수
TARGET_COUNT = sum(TICKET_CONFIG.values())

def analyze_seat_availability_lotte(driver, required_seats):
    if required_seats == 0:
        return
    
    time.sleep(1)
    try:
        seat_container = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "seat_area"))
        )
        
        container_width = seat_container.size['width']
        container_height = seat_container.size['height']
        all_seats = seat_container.find_elements(By.CSS_SELECTOR, "a.sel")
        
        seat_map = {}
        for seat in all_seats:
            if seat.get_attribute("seat-statuscode") != "0": 
                continue
                
            style_str = seat.get_attribute("style") or ""
            left_match = re.search(r"left:\s*([\d.]+)px", style_str)
            top_match = re.search(r"top:\s*([\d.]+)px", style_str)
            
            if left_match and top_match and container_width > 0 and container_height > 0:
                left = float(left_match.group(1))
                top = float(top_match.group(1))
                
                rel_x = left / container_width
                rel_y = top / container_height
                
                in_x = PREFERRED_SEAT["x_start"] <= rel_x <= PREFERRED_SEAT["x_end"]
                in_y = PREFERRED_SEAT["y_start"] <= rel_y <= PREFERRED_SEAT["y_end"]
                
                if not (in_x and in_y):
                    continue 
            
            seat_id = seat.get_attribute("data-seat")
            if not seat_id: continue
            
            match = re.match(r"([A-Za-z]+)(\d+)", seat_id)
            if match:
                row = match.group(1) 
                col = int(match.group(2)) 
                if row not in seat_map:
                    seat_map[row] = []
                seat_map[row].append(col)

        found_options = 0
        print(f"======= 지정된 좌표 범위 내 {required_seats}명이 함께 앉을 수 있는 좌석 =======")
        print("-" * 50)
        
        sorted_rows = sorted(seat_map.keys())
        for row in sorted_rows:
            cols = sorted(seat_map[row])
            available_groups = []
            
            for i in range(len(cols) - required_seats + 1):
                window = cols[i : i + required_seats]
                if window[-1] - window[0] == required_seats - 1:
                    available_groups.append(f"{window[0]}~{window[-1]}")
            
            if available_groups:
                print(f" [{row} 열] 가능한 연속 좌석: {', '.join(available_groups)}")
                found_options += len(available_groups)

        print("-" * 50)
        if found_options == 0:
            print(" -> 해당 좌표 범위 내에 요청된 인원수에 해당하는 연속 좌석이 없습니다.")
        else:
            print(f" -> 총 {found_options}개의 조합을 발견했습니다.")
            
    except Exception as e:
        print(f"  -> 좌석 분석 중 오류 발생")


# ==========================================
# 8~12. 모든 시간대 순회
# ==========================================
print("[8~12번(모든 상영 시간대 순회 및 분석)절차 진행]")
try:
    time_xpath = "//a[@role='button' and .//dd[contains(@class, 'time')]]"
    time_elements_initial = driver.find_elements(By.XPATH, time_xpath)
    
    valid_indices = []
    
    for idx, t in enumerate(time_elements_initial):
        try:
            if t.is_displayed():
                class_attr = t.get_attribute("class") or ""
                if "disabled" not in class_attr and "soldout" not in class_attr:
                    valid_indices.append(idx)
        except:
            continue
            
    if not valid_indices:
        print("  -> 화면에 표시된 예매 가능한 상영 시간이 없습니다.")
    else:
        print(f"  -> 총 {len(valid_indices)}개의 유효한 예매 가능 시간을 확인했습니다. 순차 분석을 시작합니다.\n")
        
        for i, btn_idx in enumerate(valid_indices):
            time.sleep(1.5)
            time_elements = driver.find_elements(By.XPATH, time_xpath)
            
            if btn_idx >= len(time_elements):
                continue
                
            target_btn = time_elements[btn_idx]
            
            try:
                start_time = target_btn.find_element(By.CSS_SELECTOR, "dd.time strong").text
                rest_seat = target_btn.find_element(By.CSS_SELECTOR, "dd.seat strong").text
            except:
                continue

            print("==================================================")
            print(f"[{i+1}/{len(valid_indices)}] 상영 시간: {start_time} (잔여 {rest_seat}석) 분석 시작")
            print("==================================================")
            
            driver.execute_script("arguments[0].scrollIntoView(true);", target_btn)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", target_btn)
            time.sleep(1)
            
            try:
                alert = Alert(driver)
                alert.accept()
                time.sleep(0.5)
            except:
                pass
            
            # 첫 번째 팝업창(안내창) 닫기
            try:
                popup_btns = driver.find_elements(By.CSS_SELECTOR, "button.btn_close.btnCloseLayerMulti")
                for btn in popup_btns:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
            except:
                pass

            # 두 번째 '인원/좌석 선택' 버튼 클릭
            try:
                next_step_xpath = "//a[contains(@class, 'btn_col1') and contains(text(), '인원/좌석 선택')]"
                next_step_btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, next_step_xpath)))
                driver.execute_script("arguments[0].click();", next_step_btn)
                time.sleep(2)
            except Exception as e:
                print(f"  -> '인원/좌석 선택' 버튼을 찾을 수 없어 건너뜁니다.")
                try:
                    step1_tab = driver.find_element(By.CSS_SELECTOR, "li.step01 > a")
                    driver.execute_script("arguments[0].click();", step1_tab)
                except:
                    pass
                continue

            # 인원 설정
            for ticket_type, count in TICKET_CONFIG.items():
                if count == 0:
                    continue
                selector = f"li[data-peple='{ticket_type}'] button.btn_plus"
                try:
                    target_cnt_btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    for _ in range(count):
                        driver.execute_script("arguments[0].click();", target_cnt_btn)
                        time.sleep(0.3) 
                except:
                    pass

            # 좌석 분석
            analyze_seat_availability_lotte(driver, TARGET_COUNT)
            print("\n")
            try:
                step1_tab = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "li.step01 > a"))
                )
                driver.execute_script("arguments[0].click();", step1_tab)
                time.sleep(1.5)
            except Exception as e:
                print("  -> 상영시간 화면으로 돌아가는데 실패했습니다.")

except Exception as e:
    print(f"  -> 시간 순차 분석 중 오류 발생: {e}")

print("\n=== 프로그램 종료 (정보 제공 완료) ===")
input("종료하려면 터미널에서 엔터 키를 누르세요...")