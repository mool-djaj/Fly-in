#SESSION_ID = "56836682007%3A66qHiHfuCsP5RA%3A21%3AAYkZ3s-eLA2W7kyRk7jYKd6R1coTxq_XQGJ-WZ1krw"
#SERPAPI_KEY = "a98f6bc2abecb386d1ae098942452c680383f4a4d396a3e6980efa9c68d567b3"

import math
import re
import time
import requests
from datetime import datetime
from instagrapi import Client

SESSION_ID = "56836682007%3A66qHiHfuCsP5RA%3A21%3AAYkZ3s-eLA2W7kyRk7jYKd6R1coTxq_XQGJ-WZ1krw"
SERPAPI_KEY = "a98f6bc2abecb386d1ae098942452c680383f4a4d396a3e6980efa9c68d567b3"

# --- 2. FORENSIC HELPER FUNCTIONS ---
def calculate_shannon_entropy(string: str) -> float:
    """Calculates the randomness of characters in a string to detect bot names."""
    if not string:
        return 0.0
    prob = [float(string.count(c)) / len(string) for c in dict.fromkeys(string)]
    return -sum([p * math.log2(p) for p in prob])

def check_avatar_lens(image_url: str, api_key: str) -> dict:
    """Uses Google Lens to check if the profile picture is stolen/stock."""
    if not api_key or "YOUR_SERPAPI_KEY" in api_key:
        return {"stolen": False, "match_count": 0}
    try:
        params = {"engine": "google_lens", "url": image_url, "api_key": api_key}
        res = requests.get("https://serpapi.com/search", params=params, timeout=10)
        data = res.json()
        matches = data.get("visual_matches", [])
        return {"stolen": len(matches) > 0, "match_count": len(matches)}
    except Exception as e:
        print(f"[-] Image search error: {e}")
        return {"stolen": False, "match_count": 0}

# --- 3. THE MASTER INVESTIGATION ENGINE ---
def advanced_account_audit(cl: Client, target_username: str) -> dict:
    risk_score = 0
    flags = []
    critical_flags = []
    audit_data = {}

    try:
        user = cl.user_info_by_username(target_username)
    except Exception as e:
        return {"success": False, "error": str(e)}

    # ----------------------------------------------------
    # PILLAR 1: Reverse Image Search (Google Lens)
    # ----------------------------------------------------
    if user.profile_pic_url:
        lens_result = check_avatar_lens(str(user.profile_pic_url), SERPAPI_KEY)
        if lens_result["stolen"]:
            risk_score += 85  # Massive instant penalty
            critical_flags.append(f"STOLEN AVATAR: Found {lens_result['match_count']} exact visual matches online! This is likely a fake persona.")

    if getattr(user, "has_anonymous_profile_picture", False):
        risk_score += 40
        flags.append("Default blank avatar (no profile photo set).")

    # ----------------------------------------------------
    # PILLAR 2: Handle & Identity Analysis
    # ----------------------------------------------------
    if re.search(r"\d{4,}$", user.username):
        risk_score += 25
        flags.append("Handle ends with 4+ generated numbers (bulk creation pattern).")

    entropy = calculate_shannon_entropy(user.username)
    if len(user.username) > 8 and entropy > 3.4:
        risk_score += 20
        flags.append(f"High username randomness ({entropy:.2f}): Likely machine-generated.")

    # ----------------------------------------------------
    # PILLAR 3: Disposable vs. Mass-Following Math
    # ----------------------------------------------------
    following = user.following_count
    followers = user.follower_count
    
    if followers < 40 and following < 40:
        risk_score += 45
        flags.append(f"Disposable profile pattern: Micro-audience ({followers} followers, {following} following).")
    elif followers < 15:
        risk_score += 25
        flags.append(f"Extremely low follower count ({followers}).")

    if following > 0:
        ratio = followers / following
        audit_data["ratio"] = f"{ratio:.2f}"
        
        if following > 1000 and ratio < 0.15:
            risk_score += 35
            flags.append(f"Mass following footprint: Following {following} with only {followers} followers.")
    else:
        audit_data["ratio"] = "N/A"

    if followers > 1500 and user.media_count == 0:
        risk_score += 35
        flags.append("Ghost profile: Over 1,500 followers with 0 published posts.")

    # ----------------------------------------------------
    # PILLAR 4: Account Age Verification
    # ----------------------------------------------------
    try:
        about_info = cl.about_this_account(user.pk)
        joined_date = about_info.get("date_joined", "")
        
        if joined_date:
            year_match = re.search(r'\b(20\d{2})\b', str(joined_date))
            if year_match:
                year = int(year_match.group(1))
                current_year = datetime.now().year
                age = current_year - year
                
                if age == 0:
                    risk_score += 35
                    flags.append(f"📅 Brand new account: Created this year ({year}).")
                elif age >= 3:
                    risk_score -= 40
                    flags.append(f"📅 Veteran account: Established in {year} ({age} years old).")
                else:
                    flags.append(f"📅 Account age verified: Created in {year}.")
    except Exception:
        pass

    # ----------------------------------------------------
    # PILLAR 5: Bio Threat Scanning
    # ----------------------------------------------------
    bio = (user.biography or "").lower()
    spam_triggers = ["crypto", "forex", "invest", "binary option", "whatsapp", "t.me/", "telegram", "cashapp"]
    detected_spam = [word for word in spam_triggers if word in bio]
    if detected_spam:
        risk_score += 30
        flags.append(f"Suspicious bio keywords: {', '.join(detected_spam)}.")

    # ----------------------------------------------------
    # PILLAR 6: Post Engagement (Public Profiles Only)
    # ----------------------------------------------------
    if not user.is_private and user.media_count > 0:
        try:
            recent_posts = cl.user_medias(user.pk, amount=6)
            if recent_posts:
                total_likes = sum(p.like_count for p in recent_posts)
                total_comments = sum(p.comment_count for p in recent_posts)
                avg_interactions = (total_likes + total_comments) / len(recent_posts)

                if followers > 0:
                    er = (avg_interactions / followers) * 100
                    audit_data["er"] = f"{er:.2f}%"

                    if followers >= 3000 and er < 0.15:
                        risk_score += 45
                        flags.append(f"Fake audience anomaly: Dangerously low ER ({er:.2f}%) for {followers:,} followers.")
        except Exception:
            pass
    elif user.is_private:
        risk_score += 15
        flags.append("🔒 Account is private (Posts cannot be analyzed).")

    # Final Adjustments
    if user.is_verified:
        risk_score -= 60
        flags.append("✅ Account is officially Meta verified.")

    final_score = max(0, min(risk_score, 100))

    return {
        "success": True,
        "score": final_score,
        "flags": flags,
        "critical_flags": critical_flags,
        "audit_data": audit_data,
        "username": user.username,
        "followers": followers,
        "following": following,
        "posts": user.media_count
    }

# --- 4. STATELESS DM LISTENER ---
def start_dm_listener():
    cl = Client()
    print("[*] Bypassing login screen using sessionid token...")
    
    try:
        cl.login_by_sessionid(SESSION_ID)
        me = cl.account_info()
        print(f"[+] Successfully logged in as @{me.username}. Listening for DMs...")
    except Exception as e:
        print(f"[-] Session login failed. Error: {e}")
        return

    while True:
        try:
            threads = cl.direct_threads(amount=5)
            
            for thread in threads:
                if not thread.messages:
                    continue
                    
                latest_msg = thread.messages[0]
                
                # Stateless memory: Ignore if the bot sent the last message
                if str(latest_msg.user_id) == str(cl.user_id):
                    continue
                    
                print(f"\n[*] Processing new message from user (ID: {latest_msg.id})")
                target_username = None
                
                # Extract username from text
                if latest_msg.text:
                    raw_text = latest_msg.text.strip().lower()
                    target_username = raw_text.replace("https://", "").replace("http://", "").replace("www.", "").replace("instagram.com/", "").replace("@", "").split("?")[0].strip("/")
                    
                # Extract from Profile Share Card
                elif latest_msg.item_type in ['profile', 'xma_profile'] and hasattr(latest_msg, 'profile') and latest_msg.profile:
                    target_username = latest_msg.profile.username
                    print(f"[*] Detected a Profile Share Card for @{target_username}")
                    
                if not target_username or target_username == "":
                    print(f"[-] Unsupported media type. Replying with warning.")
                    cl.direct_send("❌ Please type the username or use the 'Share Profile' button.", thread_ids=[thread.id])
                    continue
                    
                print(f"[*] Executing advanced scan for: @{target_username}")
                cl.direct_send(f"🔍 Running 6-Pillar OSINT Scan on @{target_username} (Image check may take a few seconds)...", thread_ids=[thread.id])
                
                report = advanced_account_audit(cl, target_username)
                
                # --- FORMAT THE REPORT UI ---
                if report["success"]:
                    score = report["score"]
                    if score >= 75:
                        verdict = "🚨 HIGH RISK (Likely Bot/Scammer)"
                    elif score >= 40:
                        verdict = "⚠️ SUSPICIOUS (Anomalies Present)"
                    else:
                        verdict = "✅ ORGANIC (Low Risk Profile)"

                    response = f"🛡️ OSINT AUDIT: @{report['username']}\n"
                    response += f"Threat Score: {score}/100 -> {verdict}\n"
                    response += "───────────────────\n"
                    
                    # Highlight Critical Image Threats
                    if report["critical_flags"]:
                        response += "🚨 CRITICAL ALERTS:\n"
                        for critical in report["critical_flags"]:
                            response += f"❌ {critical}\n"
                        response += "───────────────────\n"

                    response += f"👥 Followers: {report['followers']:,} | Following: {report['following']:,}\n"
                    response += f"📸 Posts: {report['posts']:,}\n"
                    
                    if "er" in report["audit_data"]:
                        response += f"📈 Engagement Rate: {report['audit_data']['er']}\n"
                        
                    response += "───────────────────\n"
                    response += "Forensic Findings:\n"
                    if not report["flags"] and not report["critical_flags"]:
                        response += "• No suspicious anomalies detected.\n"
                    for flag in report["flags"]:
                        response += f"• {flag}\n"
                else:
                    response = f"❌ Scan failed: Account does not exist or is banned."

                # Send the final report
                cl.direct_send(response, thread_ids=[thread.id])
                print("[+] Scan complete and report sent.")
                        
        except Exception as e:
            print(f"[-] Loop error: {e}")
            
        time.sleep(10)

if __name__ == "__main__":
    start_dm_listener()