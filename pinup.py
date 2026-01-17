# ... (앞부분 동일) ...

            if pos:
                driver.execute_script(f"document.elementFromPoint({pos['x']},{pos['y']}).dispatchEvent(new MouseEvent('click',{{bubbles:true}}));")
                time.sleep(10)
                
                # [이미지 전송]
                shot_name = f"top_{i+1}.png"
                driver.save_screenshot(shot_name)
                send_to_discord(THEME_WEBHOOK, f"📸 **{i+1}위 {t_name} 상세 리스트**", shot_name)

                # [핵심 수정] 빨간 박스 영역(상세 리스트)만 콕 집어서 추출
                extract_script = """
                // 1. 가장 정확한 상세 리스트 컨테이너(빨간 박스)를 찾습니다.
                var detailContainer = document.querySelector('.theme_detail_list') || 
                                     document.querySelector('.detail_list_area') ||
                                     Array.from(document.querySelectorAll('div')).find(el => el.innerText.includes('테마 상세 >')).parentElement.parentElement;
                
                if(detailContainer) {
                    // 상단 히트맵 내용은 제외하고 이 컨테이너 내부의 텍스트만 가져옵니다.
                    return detailContainer.innerText;
                }
                return "";
                """
                detail_text = driver.execute_script(extract_script)
                
                # 정규식: 글자로 시작하는 종목명(2~12자) + 등락률
                matches = re.findall(r'([가-힣A-Za-z][가-힣A-Za-z0-9&]{1,12})\s*[0-9,]*\s*([+-]?\d+\.\d+%)', detail_text)
                
                s_seen = set()
                for s_name, s_rate in matches:
                    clean_s_name = s_name.strip()
                    
                    # 테마 이름(반도체, 바이오 등)이 종목으로 들어오는 것 방지
                    if clean_s_name and clean_s_name not in theme_names and clean_s_name not in s_seen:
                        # 숫자로만 된 찌꺼기 제외
                        if clean_s_name.isdigit(): continue
                            
                        stocks_info.append(f"{clean_s_name} {s_rate}")
                        collected_for_start.append(clean_s_name)
                        s_seen.add(clean_s_name)
                    
                    if len(stocks_info) >= 5: break

# ... (뒷부분 동일) ...
