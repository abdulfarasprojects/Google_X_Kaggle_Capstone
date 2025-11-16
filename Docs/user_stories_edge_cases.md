# Weight Loss Chat Agent: User Stories & Edge Cases

**Document Version:** 1.0  
**Last Updated:** November 16, 2025  
**Platform:** Telegram  
**Focus:** All user journeys, edge cases, and failure scenarios

---

## Table of Contents

1. [User Story Format & INVEST Criteria](#user-story-format--invest-criteria)
2. [Core User Stories](#core-user-stories)
3. [Nudge Agent User Stories](#nudge-agent-user-stories)
4. [Batch Processing User Stories](#batch-processing-user-stories)
5. [Edge Cases & Failure Scenarios](#edge-cases--failure-scenarios)
6. [Critical Bugs & Agent Failures](#critical-bugs--agent-failures)
7. [Recovery Strategies](#recovery-strategies)
8. [Testing Scenarios](#testing-scenarios)

---

## User Story Format & INVEST Criteria

All user stories follow this format:

```
As a [persona],
I want to [action],
so that [benefit/outcome].

Acceptance Criteria:
- [ ] Criterion 1
- [ ] Criterion 2

Edge Cases to Consider:
- Edge case 1
- Edge case 2

Priority: [Must Have / Should Have / Could Have]
Story Points: [1-13]
```

### INVEST Criteria

Each story is:
- **Independent** - Can be developed without other stories
- **Negotiable** - Details can be discussed/refined
- **Valuable** - Delivers user value
- **Estimable** - Team can size it
- **Small** - Completable in one sprint
- **Testable** - Clear acceptance criteria

---

## Core User Stories

### **USER STORY 1: User Onboarding & Profile Setup**

```
As a new user,
I want to set up my profile with my weight, height, age, and weight loss goal,
so that the agent can personalize my recommendations and track my progress accurately.

Acceptance Criteria:
- [ ] User can complete onboarding in <2 minutes
- [ ] Profile fields: age, height, weight, target weight, activity level, goal deficit
- [ ] User sees confirmation of saved profile
- [ ] Bot calculates daily calorie goal from profile data
- [ ] User can edit profile anytime via /profile command
- [ ] System validates inputs (age 18-100, height/weight reasonable ranges)

Edge Cases:
- User enters negative age/weight
- User enters extremely high values (500 kg weight, 250 cm height)
- User enters non-numeric values
- User cancels onboarding mid-way
- User tries to set calorie goal lower than 1000 cal/day (dangerously low)
- User sets target weight same as current weight (zero deficit goal)
- User sets target weight higher than current weight (weight gain goal)
- Profile already exists, user starts new conversation (should restore session)

Priority: MUST HAVE
Story Points: 5
```

**Implementation Notes:**
- Validate all inputs on tool level
- Guardrail: Reject calorie goals <1000 or >3000
- Guardrail: Warn if deficit >1000 cal/day (unsustainable)
- Store profile in session state with timestamp

---

### **USER STORY 2: Log Single Meal (Simple)**

```
As a user,
I want to log a meal I just ate by describing it in natural language,
so that I can quickly record my food intake without complex menus.

Acceptance Criteria:
- [ ] User can type "Had 2 eggs and toast"
- [ ] Bot asks "Is that all for this meal?"
- [ ] Bot collects all meal items before processing
- [ ] Bot queries USDA database for nutrition
- [ ] Bot displays: total calories, protein, confidence level
- [ ] Bot shows remaining calorie budget for the day
- [ ] Meal is stored in session memory with timestamp

Edge Cases:
- User says "food" (too vague)
- User says "some eggs" (quantity unclear)
- User enters food not in USDA database (obscure dish)
- User enters typo (e.g., "egggs")
- User enters non-food item (e.g., "water" under meals)
- User enters meal at 2:30 AM (valid, but unusual time)
- User enters past meal without time context
- User enters future meal ("I will eat...tomorrow")
- Batch collection timeout (user says "Is that all?" after 5 min silence)
- User enters meal with extremely high calories (5000+ cal claim)
- User enters meal with 0 calories (dietary water)

Priority: MUST HAVE
Story Points: 5
```

**Implementation Notes:**
- Batch collection max items: 10 per meal
- Timeout if no input for 15 min → assume batch complete
- Guardrail: Flag meals >1500 cal as "large meal, verify accuracy"
- Guardrail: Flag meals <100 cal as "light snack, missing items?"
- Use fuzzy matching for typos (levenshtein distance)
- Fallback: If USDA fails, query Nutritionix
- If both fail: Ask user for manual calorie entry

---

### **USER STORY 3: Log Complete Breakfast (Multi-Item Batch)**

```
As a busy user,
I want to log a multi-item breakfast (eggs, toast, juice, coffee),
so that I can capture the full meal without re-entering each item separately.

Acceptance Criteria:
- [ ] User enters first item "2 eggs"
- [ ] Bot asks "Anything else for breakfast?"
- [ ] User adds "toast" → Bot still asks
- [ ] User adds "OJ" → Bot asks again
- [ ] User adds "coffee" → Bot asks
- [ ] User says "that's all"
- [ ] Bot processes ALL 4 items as single breakfast batch
- [ ] Bot returns: Total 420 cal, 16g protein for breakfast
- [ ] Each item shows individual contribution
- [ ] Confidence score shown per item

Edge Cases:
- User adds contradictory items ("bacon" then "I meant fish not bacon")
- User adds same item twice ("eggs" then "eggs again")
- User says "that's all" after first item
- User says "nothing" or "never mind" → cancel batch
- User skips breakfast, jumps to lunch
- User logs breakfast 3 times in one day
- User adds 15 items (excessive)
- User adds 0 items (empty batch)
- Network timeout mid-batch collection
- Bot crashes after collecting 3 items
- User tries to log meal from yesterday (time context)

Priority: MUST HAVE
Story Points: 8
```

**Implementation Notes:**
- Batch state stored in session with timestamp
- Max batch size: 10 items per meal
- Deduplication: If same food logged twice, ask "Did you mean both or just one?"
- Keep batch in memory while collecting (not persisted until confirmed)
- If session crashes: Restart batch collection

---

### **USER STORY 4: Log Workout Session (Multi-Exercise Batch)**

```
As a gym user,
I want to log a complete workout session with multiple exercises,
so that the agent can track my volume and suggest progression.

Acceptance Criteria:
- [ ] User enters "10 pull-ups"
- [ ] Bot asks "Any more sets of pull-ups or different exercise?"
- [ ] User adds "3 sets of 8 squats at 185 lbs"
- [ ] User adds "20 push-ups"
- [ ] User says "that's all"
- [ ] Bot calculates total volume:
  - Pull-ups: 10 reps (1 set)
  - Squats: 24 reps total (3 sets × 8)
  - Push-ups: 20 reps (1 set)
- [ ] Bot suggests progression (e.g., "Next week, try 185 lbs × 10 on squats")
- [ ] Includes form tips for compound lifts
- [ ] Workout stored with timestamp and body part focus

Edge Cases:
- User enters weight without unit ("185" → assume lbs, ask to confirm)
- User enters reps without sets ("10 pull-ups" → assume 1 set, ask to confirm)
- User enters sets/reps backwards ("8 sets of 3 squats" → verify)
- User enters extremely heavy weight (1000 lbs)
- User enters 0 reps ("0 pull-ups")
- User enters 1000 reps (physically impossible)
- User enters exercise name with typo ("squatz")
- User enters made-up exercise ("extreme mega flex")
- User enters bodyweight exercise with weight ("50 kg bicep curl" for push-ups)
- User logs workout at 3 AM
- User logs same workout 5 times in one day
- User enters rest day ("Rest day, no workout")
- User attempts progression but never completed original (new user, no history)
- User logs workout after 10+ days of rest (recovery week)
- Batch collection fails mid-way

Priority: MUST HAVE
Story Points: 8
```

**Implementation Notes:**
- Parse patterns: "[quantity] [unit?] [exercise]" or "[sets] sets of [reps] [exercise] at [weight]"
- Regex: `\d+\s*(sets?\s+of\s+)?\d+\s*(reps?|rep)?\s+([a-zA-Z\s]+)(\s+at\s+(\d+)\s*(lbs?|kg))?`
- Guardrail: Flag if weight >500 lbs (unrealistic)
- Guardrail: Flag if reps >500 (unrealistic)
- Form tips database: common compound lifts (pull-ups, squats, deadlifts, bench)

---

### **USER STORY 5: Log Water Intake**

```
As a user,
I want to log my water intake throughout the day,
so that I can ensure I'm hydrated and meeting my daily goal.

Acceptance Criteria:
- [ ] User can log in multiple units: "2 glasses", "500 ml", "1 liter"
- [ ] Bot converts to ounces for standard measurement
- [ ] Bot shows progress toward daily goal (8-10 glasses)
- [ ] User can log multiple times: morning water, afternoon water, evening water
- [ ] Daily hydration summary shows: logged today, remaining goal
- [ ] Bot suggests hydration nudges if behind schedule

Edge Cases:
- User logs "water" without quantity (assume 1 glass, ask to confirm)
- User logs "0 glasses"
- User logs 100 liters (unrealistic)
- User logs negative amount ("-5 glasses")
- User logs mixed drinks as water ("coffee with water")
- User logs water multiple times in same minute (potential spam/error)
- User logs water after midnight (should it count toward today or tomorrow?)
- User logs water with typo ("watar", "H20")
- User logs water in non-standard format ("a cup", "a sip", "a splash")
- User timezone changes mid-day (edge case for daily boundaries)

Priority: MUST HAVE
Story Points: 3
```

**Implementation Notes:**
- Standard conversion: 1 glass = 8 oz = 240 ml
- Accept formats: glasses, oz, ml, liters, cups
- Guardrail: Flag if daily total >15 liters (possible overhydration risk)
- Fuzzy matching for typos (H2O → water, watar → water)

---

### **USER STORY 6: Log Sleep**

```
As a user,
I want to log my sleep duration and quality,
so that I can correlate sleep with weight loss and workout performance.

Acceptance Criteria:
- [ ] User enters sleep in hours: "7 hours", "7.5 hours", "7 hours 30 min"
- [ ] User enters sleep quality as 1-10 scale: "quality 8/10"
- [ ] Bot validates: 4-12 hours reasonable range
- [ ] Bot validates: quality 1-10 scale
- [ ] Sleep logged with date (previous night's sleep)
- [ ] Weekly sleep quality trend shown
- [ ] Sleep correlated with workout performance (tired → suggest light workout)
- [ ] Sleep correlated with weight gain (poor sleep linked to plateau)

Edge Cases:
- User logs "0 hours" (didn't sleep)
- User logs "24 hours" (unrealistic)
- User logs quality as "11/10" (out of range)
- User logs quality as "really good" (text instead of number)
- User logs quality as "-5" (negative)
- User logs sleep at 10 AM after night shift (previous night but current day)
- User logs sleep without time context (which night?)
- User forgets to log sleep for 5 days, then logs all 5 days
- User logs sleep twice same day
- User logs sleep improvement/decline to therapist (outside scope)
- User logs insomnia-related distress (mental health crisis)

Priority: MUST HAVE
Story Points: 4
```

**Implementation Notes:**
- Parse sleep format: "\d+\.?\d*\s*hours?" or "\d+\s*hours?\s*\d+\s*min"
- Quality format: "\d+\s*/?\s*10" or "quality\s*:?\s*(\d+)"
- Guardrail: Flag if <5 hours → recovery risk, suggest light workout
- Guardrail: Flag if 3-night average <6 hours → suggest sleep focus nudge
- Correlate with weight trends: Poor sleep + plateau = suggest better sleep

---

### **USER STORY 7: Log Daily Steps**

```
As a user,
I want to log my daily step count,
so that I can track my non-exercise activity and reach my step goal.

Acceptance Criteria:
- [ ] User enters daily steps: "12,500 steps"
- [ ] Bot accepts formats: "12500", "12,500", "12k"
- [ ] Bot shows progress toward goal (default 10,000)
- [ ] Bot shows weekly step trend (trending up/down)
- [ ] User can manually override auto-count if different from wearable

Edge Cases:
- User enters "0 steps" (sedentary day)
- User enters "1,000,000 steps" (impossible)
- User enters negative steps ("-5000")
- User enters steps as "lots", "many", "some" (non-numeric)
- User logs steps twice same day (should replace or add?)
- User logs steps for past 7 days (bulk entry)
- User logs steps in miles instead of steps (confusion)
- User claims step count 3x higher than usual (possible error or activity boost)
- Timezone edge case: User logs steps at 11:59 PM vs 12:01 AM

Priority: SHOULD HAVE
Story Points: 3
```

**Implementation Notes:**
- Accept formats: numeric, "k" suffix (12k = 12,000), comma separators
- Guardrail: Flag if >50,000 steps (unusual, but possible)
- Guardrail: Flag if <500 steps (sedentary day warning)
- On bulk entry (past dates): Confirm before storing
- Trending: Calculate 7-day moving average, show direction

---

### **USER STORY 8: View Today's Progress**

```
As a user,
I want to see a summary of my progress today across all 6 metrics,
so that I can understand my current status and make decisions for remaining day.

Acceptance Criteria:
- [ ] Command: /stats or "Show today's progress"
- [ ] Summary includes:
  - Calories: logged vs goal, remaining budget
  - Protein: logged vs goal, % of target
  - Water: logged vs goal, glasses remaining
  - Sleep: (from last night) hours and quality
  - Steps: logged today vs goal
  - Workouts: completed sessions, volume
- [ ] Color/emoji indicators: ✅ on track, ⚠️ behind, 🔥 ahead
- [ ] Suggestions based on gaps (e.g., "300 cal remaining, try protein snack")

Edge Cases:
- User checks stats at midnight (data boundary)
- User checks stats before logging anything today
- User checks stats for different day (e.g., "yesterday stats")
- User's profile not set up (no goal to compare against)
- Timezone misalignment (UTC vs local time)
- Multiple sessions in one day (stats should aggregate)
- Data corruption: missing some daily logs

Priority: MUST HAVE
Story Points: 5
```

**Implementation Notes:**
- Real-time calculation from session state
- Aggregate all logs for current date
- Compare against user goals in profile
- Fuzzy time boundaries: count logs from 12 AM to 11:59 PM user's timezone

---

### **USER STORY 9: View Weekly Report**

```
As a user,
I want to see a comprehensive weekly summary every Sunday,
so that I can assess my progress and plan for the coming week.

Acceptance Criteria:
- [ ] Automatic report sent Sunday 18:00
- [ ] Report includes:
  - Avg daily calorie deficit
  - Protein consistency (% days meeting target)
  - Water intake trend
  - Average sleep quality
  - Total steps logged
  - Workout frequency
  - Logging streak (consecutive days logged ≥1 metric)
  - Best metric of the week ("Hero stat")
- [ ] Trend arrows: ↗️ improved, ↘️ declined, → stable
- [ ] User can request early report: /report command

Edge Cases:
- User just joined mid-week (<7 days data)
- User has 0 logs for entire week
- User has only 1 log for entire week
- User changed timezone mid-week
- Weekly boundary: Sunday 18:00 in different timezones
- Report requested on Monday (should show last week)
- Report requested on Saturday (should show week-to-date)
- Inconsistent data: gaps in consecutive days

Priority: SHOULD HAVE
Story Points: 8
```

**Implementation Notes:**
- Automatic dispatch: Sunday 18:00 user's timezone
- Week definition: Sunday 00:00 - Saturday 23:59
- If <3 days data: Send partial report with note "Only [X] days of data so far"
- Hero stat logic: Metric with highest % goal achievement

---

### **USER STORY 10: Viewing Logging Streak**

```
As a user,
I want to see my logging streak (consecutive days I've logged something),
so that I can stay motivated and see my consistency.

Acceptance Criteria:
- [ ] User can check /streak command
- [ ] Shows: Current streak, longest streak, days since break
- [ ] Definition: Logged at least 1 metric per day (any of 6 areas)
- [ ] Breaks streak if: 0 logs for entire calendar day
- [ ] Streak protects: Nudge at 23:55 if at risk
- [ ] Can resume streak if: Log within 24 hours after break

Edge Cases:
- Streak started before this week
- User travels across timezones (day boundary changes)
- User logs at 11:59 PM then 12:01 AM (same log? different days?)
- User logs only water for entire week (counts as streak despite no calories)
- Streak broken during sleep (midnight to midnight boundary)
- User tries to extend non-existent streak (just started)
- User wants to know "streak for workouts only" (separate??)
- Streak display when current streak = 0

Priority: SHOULD HAVE
Story Points: 3
```

**Implementation Notes:**
- Day boundary: User's local timezone midnight
- Streak counter: Incremented at first log after midnight
- Streak breaks: If 24h pass without any log

---

## Nudge Agent User Stories

### **USER STORY 11: Morning Motivational Nudge**

```
As a user,
I want to receive a morning nudge with encouragement,
so that I start my day motivated and reminded to track my progress.

Acceptance Criteria:
- [ ] Nudge arrives at 07:00 (user's preferred time)
- [ ] Personalized based on previous day's performance:
  - If yesterday logged: "Great consistency! 5-day streak. Let's extend it 💪"
  - If yesterday skipped: "New day, fresh start! You got this 🚀"
  - If first time: "Good morning! Ready to start tracking today?"
- [ ] No nudge if user hasn't completed onboarding
- [ ] Can customize nudge time via /settings
- [ ] User can snooze nudge (15 min, 1 hour, ask later)
- [ ] User can disable morning nudges

Edge Cases:
- User disabled push notifications (message still in Telegram)
- User timezone changed since last nudge
- Nudge scheduled but user already awake and using app
- Nudge arrives at 3 AM for user in different timezone
- User account suspended/deleted
- Duplicate nudge sent (system bug)
- User's daily cadence doesn't start at 7 AM (shift worker)
- Nudge sent but message fails to deliver (network issue)
- User changes time zone mid-morning

Priority: SHOULD HAVE
Story Points: 5
```

**Implementation Notes:**
- APScheduler job: Recurring daily at user's timezone
- Personalization: Query last 24h logs from session
- Disable option: `disable_nudges` flag in user profile
- Snooze: Reschedule job for +15min, +1hr, or next day

---

### **USER STORY 12: Midday Activity Check**

```
As a user,
I want to receive a midday nudge checking my activity,
so that I can log meals and stay on track.

Acceptance Criteria:
- [ ] Nudge arrives at 12:00 (lunch time)
- [ ] Check: Any meals logged yet today?
- [ ] If YES: "On track! Keep it going 🔥"
- [ ] If NO: "Time for lunch? Ready to log? 🍽️"
- [ ] Shows: Calorie budget remaining so far
- [ ] Suggests: "Try protein with lunch for satiety"
- [ ] Can dismiss or snooze

Edge Cases:
- User logs meal right after morning nudge (redundant)
- User ate breakfast, no lunch planned (unusual schedule)
- User works night shift (noon is midnight for them)
- User logs while nudge is being sent (race condition)
- Nudge arrives but user unavailable (traveling)
- User snoozes 5 times (multiple snoozes)
- User deletes message accidentally

Priority: SHOULD HAVE
Story Points: 4
```

**Implementation Notes:**
- Query logs from 00:00 to current time today
- Count meals (breakfast, lunch, etc.)
- Suggestions: Personalized based on profile

---

### **USER STORY 13: Evening Nudge with Focus Goal**

```
As a user,
I want to receive an evening nudge highlighting one goal to focus on tomorrow,
so that I don't feel overwhelmed and can prioritize my efforts.

Acceptance Criteria:
- [ ] Nudge arrives at 19:00 (evening)
- [ ] Algorithm selects ONE goal with lowest adherence last 7 days:
  - If protein <80%: "🥚 Focus tomorrow: Hit your protein goal"
  - If steps <70%: "👟 Focus tomorrow: 10,000 steps"
  - If water <60%: "💧 Focus tomorrow: Hydration"
  - If workouts <50%: "💪 Focus tomorrow: Get a session in"
  - If sleep <40%: "😴 Focus tomorrow: 8 hours sleep"
  - If calories >120% deficit: "🍽️ Focus tomorrow: Stay within range"
- [ ] Each day: Different goal (rotate)
- [ ] If all goals equal: Show strongest area (rotate)
- [ ] Goal changes daily, not mid-day

Edge Cases:
- All 6 goals equally bad (equal adherence)
- User has no data yet (first day)
- User perfect on all goals (show "You're crushing it!")
- User terrible on all goals (show 2 most urgent?)
- Goal already focused yesterday (rotate to next)
- Weekend vs weekday (different goals?)
- User disabled nudges for this type

Priority: SHOULD HAVE
Story Points: 6
```

**Implementation Notes:**
- Adherence calculation: % of past 7 days goal met
- Goal rotation: Store `last_focus_goal` in session, don't repeat next day
- If tie: Alphabetical order tiebreaker

---

### **USER STORY 14: Streak Protection Nudge (23:55)**

```
As a user,
I want to receive a gentle nudge at 23:55 if I haven't logged anything today,
so that I can quickly log before midnight to keep my streak alive.

Acceptance Criteria:
- [ ] Triggers at 23:55 only if: 0 logs for entire day
- [ ] Message: "5 min left to keep your 7-day streak alive! Quick log? ⏰"
- [ ] Tone: Gentle, not pushy or shaming
- [ ] One nudge only (not 23:56, 23:57, 23:58)
- [ ] User can dismiss and let streak break (opt-in)
- [ ] If user logs before midnight: Streak continues
- [ ] If user logs after midnight: Streak breaks, but new day starts

Edge Cases:
- User already logged something today (shouldn't send)
- User doesn't have active streak (new user)
- User logged at 23:50 (already has streak, no nudge)
- User logs exactly at midnight (which day?)
- User's timezone is UTC-12 (last timezone on Earth)
- User's timezone is UTC+14 (first timezone on Earth)
- User disabled nudges (don't send)
- System sends nudge twice (duplicate)
- User disabled notifications but nudge still queued

Priority: SHOULD HAVE
Story Points: 3
```

**Implementation Notes:**
- Guard: Check if logs exist for current day before sending
- Time: Must be exactly 23:55, not range
- Cancel previous job if user logs between 23:55 and midnight

---

### **USER STORY 15: Weekly Synthesis Report (Sunday 18:00)**

```
As a user,
I want to receive a comprehensive weekly report every Sunday,
so that I can celebrate wins and plan for the next week.

Acceptance Criteria:
- [ ] Sent automatically Sunday 18:00
- [ ] Report includes:
  - Logging streak (consecutive days)
  - Daily calorie deficit average
  - Protein consistency (% days on target)
  - Water intake trend (↗️↘️→)
  - Sleep quality average
  - Total workouts completed
  - Total steps logged
  - Hero stat: Best metric of week
- [ ] Personalized section:
  - "You crushed [metric] this week! 🏆"
  - "Focus for next week: [lowest metric]"
- [ ] Celebratory tone with emojis
- [ ] One message or split into 2-3 if long

Edge Cases:
- User just joined mid-week (only 2-3 days data)
- User has 0 logs for entire week
- User has 1-2 logs only
- Timezone boundary: Sunday 18:00 ambiguous
- User deleted all data this week
- Report shows negative trends across board (demotivating?)
- User banned/suspended before report time
- Report fails to send (try retry? or skip?)
- User timezone changed mid-week

Priority: SHOULD HAVE
Story Points: 8
```

**Implementation Notes:**
- Week definition: Sunday 00:00 - Saturday 23:59
- If <2 days data: Partial report with note
- If 0 logs: Encouragement message, invite to start
- Retry: 3 attempts if delivery fails

---

## Batch Processing User Stories

### **USER STORY 16: Complete Meal Batch Confirmation**

```
As a user,
I want to confirm when my meal batch is complete,
so that the agent can process all items together accurately.

Acceptance Criteria:
- [ ] User logs "2 eggs"
- [ ] Bot asks "Is that all for this meal?"
- [ ] User can respond: "yes", "that's all", "done", "no more"
- [ ] User can respond: "no" or "more" to add more items
- [ ] User can respond: "cancel" to discard batch
- [ ] Once confirmed, bot shows:
  - All items collected
  - Total calories
  - Total protein
  - Confidence per item
  - Daily budget remaining
- [ ] Batch stored with timestamp

Edge Cases:
- User says "yes" after first item (incomplete batch, but confirmed)
- User says "no" 10 times (long batch collection)
- User says "maybe" (unclear response, ask to clarify)
- User says nothing for 15 minutes (timeout)
- User types emoji instead of response 😂 (unclear intent)
- User batch was already confirmed, tries to add again (start new batch)
- Telegram message lost/not delivered
- Bot crashes mid-batch, user retries
- User batch spans across midnight (breakfast ends after midnight)

Priority: MUST HAVE
Story Points: 4
```

**Implementation Notes:**
- Accept variations: yes, yep, ya, no, nope, nah, more, add, done, finish, cancel, quit, exit
- Fuzzy matching: If confidence <0.6 → ask to clarify ("Did you mean 'yes' or 'no'?")
- Timeout: If >15 min silence → assume batch complete, process what exists
- Batch state: Stored in session with timestamp, persists across message gaps

---

### **USER STORY 17: Workout Session Batch Processing**

```
As a user,
I want to log multiple exercises in one session,
so that the agent can calculate total volume and suggest progression.

Acceptance Criteria:
- [ ] User logs "3 sets of 8 pull-ups"
- [ ] Bot asks "Any more sets of pull-ups or different exercise?"
- [ ] User adds "20 push-ups"
- [ ] Bot processes batch as complete workout
- [ ] Bot calculates:
  - Total pull-ups: 24 reps (3×8)
  - Total push-ups: 20 reps (1×20)
  - Volume per muscle group
  - Total session duration estimate
  - Suggests progression for next time
- [ ] Stores complete session with all exercises

Edge Cases:
- User logs same exercise twice in same session (intentional super-set?)
- User logs contradictory exercises (upper body then "full body" later)
- User logs 15 different exercises (excessive)
- User logs only 0.5 sets (partial set)
- User forgets weight for some exercises but not others
- User logs rest time (should this be part of session?)
- User logs warm-up separately (count as session?)
- Batch timeout mid-session (process what exists?)
- User logs same weight but higher reps (is this progression?)
- Bot fails to parse one exercise but not others (partial failure)

Priority: MUST HAVE
Story Points: 6
```

**Implementation Notes:**
- Super-set handling: Same exercise listed twice → ask "How many total reps?"
- Volume calculation: Sum all sets × reps per exercise
- Progression logic: Look at history, suggest +2-5 lbs or +2 reps
- Timeout: Same as meal batch (15 min)

---

### **USER STORY 18: Hydration Batch (Multiple Water Logs)**

```
As a user,
I want to log multiple water intake sessions throughout the day,
so that the agent can aggregate total daily hydration.

Acceptance Criteria:
- [ ] Morning: "Drank 2 glasses" → logged
- [ ] Midday: "500ml water" → logged and summed
- [ ] After gym: "1 liter" → logged and summed
- [ ] Evening: "2 more glasses" → logged and summed
- [ ] Bot shows daily total: 8 glasses + 500ml + 1L = 12.5 glasses
- [ ] Each log stored separately with timestamp
- [ ] Daily total aggregated for stats

Edge Cases:
- User logs water 10 times in 1 hour (possible spam/error)
- User logs water in different units each time (confusing)
- User logs "water" but means coffee/tea/juice (misclassification)
- User logs negative water ("I drank -2 glasses" undo?)
- User logs past water (morning: "I drank 2 glasses at 6 AM" now it's noon)
- User logs future water ("I will drink tomorrow")
- User logs water for entire week in bulk
- User timezone changes mid-day (affects daily total)

Priority: SHOULD HAVE
Story Points: 3
```

**Implementation Notes:**
- Each log independent, stored separately
- Batch concept: "Daily" is the batch (multiple logs = one day's total)
- Sum all logs for current day
- Ignore negative values with message "Did you mean +2 glasses?"

---

## Edge Cases & Failure Scenarios

### **EDGE CASE 1: USDA API Timeout**

```
Scenario:
- User logs "2 eggs"
- Agent queries USDA FDC API
- USDA API takes >10 seconds to respond
- Timeout occurs

Current Behavior:
❌ Agent stuck waiting
❌ User sees nothing
❌ No fallback triggered

Desired Behavior:
✅ Agent catches timeout after 5 seconds
✅ Switches to Nutritionix API
✅ If Nutritionix also fails, uses local database
✅ If all fail, asks user for manual entry: "Can't look up nutrition. Estimate calories?"
✅ Confidence score: 0.3 (low confidence flagged)

Implementation:
```python
try:
    # Query USDA API with 5 sec timeout
    nutrition = await usda_api.query_food(food_name, timeout=5)
except asyncio.TimeoutError:
    # Fallback 1: Nutritionix
    nutrition = await nutritionix_api.query_food(food_name)
except Exception:
    # Fallback 2: Local database
    nutrition = local_food_db.lookup(food_name)
    if not nutrition:
        # Fallback 3: Ask user
        return {
            "status": "ask_user",
            "message": "Couldn't look up nutrition for 'eggs'. Can you estimate calories? (e.g., 150)"
        }
```

Recovery: User can always provide manual calorie entry
```

---

### **EDGE CASE 2: Batch Collection Timeout**

```
Scenario:
- User logs "2 eggs"
- Bot asks "Anything else?"
- User doesn't respond for 20 minutes
- User returns and sends "toast"

Current Behavior:
❌ Old batch state lost
❌ Toast treated as new meal
❌ "2 eggs" never logged

Desired Behavior:
✅ If user sends anything within 30 min: Resume batch
✅ If user sends after 30 min: Start fresh batch, log eggs first
✅ Clear message: "Your batch expired. Let's start fresh: What did you eat?"
✅ Offer to re-add old items: "Want me to log the 2 eggs again?"

Implementation:
```python
batch_state = session.get("batch_data", {})
batch_timestamp = batch_state.get("created_at", 0)
elapsed = time.time() - batch_timestamp

if elapsed > 30 * 60:  # 30 minutes
    # Batch expired
    return {
        "status": "batch_expired",
        "message": "Your batch expired. Let me log the eggs first, then we'll collect new items.",
        "previous_items": batch_state["items"],
        "action": "process_expired_batch"
    }
```

---

### **EDGE CASE 3: Negative/Impossible Values**

```
Scenarios:
1. User: "Ate -500 calories" (negative calories)
2. User: "50,000 calories for lunch" (impossible)
3. User: "Drank -2 liters" (negative water)
4. User: "Did 1000 pull-ups" (impossible reps)
5. User: "Weighed -80 kg" (negative weight)

Desired Behavior:
✅ Guardrail catches immediately
✅ No processing, ask for clarification
✅ Non-judgmental message
✅ Suggest reasonable values

Implementation:
```python
def validate_calorie_entry(calories: int) -> Dict:
    if calories < 0:
        return {
            "status": "invalid",
            "message": "Calories can't be negative. Did you mean positive?",
            "suggested_action": "ask_for_clarification"
        }
    
    if calories > 1500:  # Single meal unlikely >1500
        return {
            "status": "unusual",
            "message": f"{calories} calories seems high for one meal. Verify accuracy?",
            "suggested_action": "ask_for_confirmation",
            "proceed_if": "user_confirms"
        }
    
    return {"status": "valid"}
```

---

### **EDGE CASE 4: Batch Item Contradictions**

```
Scenario:
- User: "Ate 2 eggs"
- User: "Actually, I meant fish not eggs"
- Bot still has "eggs" in batch

Current Behavior:
❌ Both eggs and fish logged
❌ Calorie estimate wrong
❌ User frustrated

Desired Behavior:
✅ Ask for clarification: "Replace eggs with fish, or both?"
✅ User: "Replace"
✅ Update batch: Remove eggs, add fish
✅ Confirm new total

Implementation:
```python
def handle_contradiction(batch_items: List[str], new_item: str, replace_word: str):
    if replace_word in batch_items:
        return {
            "status": "clarify",
            "message": f"Replace '{replace_word}' with '{new_item}', or have both?",
            "options": ["Replace", "Both", "Cancel"]
        }
    else:
        batch_items.append(new_item)
        return {"status": "added", "items": batch_items}
```

---

### **EDGE CASE 5: Emotional Crisis During Logging**

```
Scenario:
- User logging meal
- Message: "Ugh I'm so fat 😞"

Current Behavior:
❌ Bot continues with calorie calculation
❌ Ignores emotional state
❌ User feels judged

Desired Behavior:
✅ Sentiment detected: -0.8 (guilt/shame)
✅ Meal still logged (functional goal)
✅ BUT response includes empathy
✅ Tone non-judgmental
✅ Offer support: "Want to chat with support?"

Implementation:
```python
sentiment = detect_sentiment(user_message)

if sentiment["score"] < -0.6:
    # High negative emotion
    return {
        "status": "log_with_empathy",
        "log_meal": True,  # Still process
        "response_tone": "supportive",
        "message": """
I hear you're struggling right now.
Here's what I logged: 300 cal, 12g protein ✅
Remember: Progress isn't linear. One meal doesn't define your journey.
Want to talk? /support
        """,
        "alert_severity": sentiment["score"] < -0.8 ? "high" : "medium"
    }
```

---

### **EDGE CASE 6: Multi-Timezone User**

```
Scenario:
- User in New York: Logs meal at 11:59 PM EST
- Travels to London (5 hours ahead)
- Logs meal at 12:01 AM GMT (same absolute time, next day)

Current Behavior:
❌ Confusing daily boundaries
❌ Streak broken due to timezone mismatch
❌ Same physical meal split across 2 days

Desired Behavior:
✅ Use user's local timezone consistently
✅ When timezone changes: Ask user's new timezone
✅ Re-calculate all previous logs with new timezone
✅ Streak maintained across timezone change
✅ Clear message: "Detected timezone change. Updated all your data."

Implementation:
```python
def handle_timezone_change(old_tz: str, new_tz: str, logs: List[Dict]):
    # Re-timestamp all logs from old to new timezone
    adjusted_logs = []
    for log in logs:
        # Convert timestamp from old_tz to new_tz
        adjusted_logs.append(adjust_timestamp(log, old_tz, new_tz))
    
    # Update session
    session["user_timezone"] = new_tz
    session["logs"] = adjusted_logs
    
    return {
        "status": "timezone_updated",
        "message": "Timezone updated. Your data is accurate.",
        "streak_status": "maintained"
    }
```

---

### **EDGE CASE 7: Session Crash & Recovery**

```
Scenario:
- User collecting meal batch (3 items logged)
- Server crashes
- User reconnects 5 minutes later

Current Behavior:
❌ Batch lost
❌ User frustrated, doesn't re-enter
❌ Meal unlogged

Desired Behavior:
✅ Session persisted to database
✅ User reconnects: "Welcome back! You were collecting a meal."
✅ Show previous batch items: ["2 eggs", "toast"]
✅ Ask: "Continue with this batch? (Add more or finish?)"
✅ User: "Finish"
✅ Meal processed successfully

Implementation:
```python
# Before crash
async def save_session_to_db(session_id: str, state: Dict):
    db.sessions.insert({
        "session_id": session_id,
        "state": state,
        "saved_at": datetime.now()
    })

# After reconnect
async def restore_session(session_id: str):
    saved = db.sessions.find_one({"session_id": session_id})
    if saved and saved["state"].get("batch_in_progress"):
        return {
            "status": "batch_recovered",
            "message": "Collecting meal batch. Items so far: " + str(saved["state"]["batch_items"]),
            "batch_data": saved["state"]
        }
```

---

## Critical Bugs & Agent Failures

### **BUG 1: Infinite Retry Loop**

```
Root Cause:
- Tool throws error
- Agent retries automatically
- Tool still throws error (hard failure, not transient)
- Agent retries forever

Symptoms:
- User message never answered
- Bot appears frozen
- CPU high due to infinite retry

Solution:
- Max retries: 3
- Different backoff strategy: exponential (1s, 2s, 4s)
- After 3 failures: Escalate to user with error message

Code:
```python
async def call_tool_with_retries(tool_func, *args, **kwargs):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await tool_func(*args, **kwargs)
            return result
        except Exception as e:
            wait_time = 2 ** attempt  # 1, 2, 4 seconds
            if attempt < max_retries - 1:
                await asyncio.sleep(wait_time)
            else:
                # Max retries reached
                return {
                    "status": "error",
                    "message": "Tool failed after 3 attempts",
                    "escalate": True
                }
```
---

### **BUG 2: Data Duplication**

```
Root Cause:
- User logs meal
- Network delay causes bot to ask "Is that all?" twice
- User responds to both, meal logged twice

Symptoms:
- Daily calorie count doubled
- User confused about statistics

Solution:
- Unique batch ID (UUID)
- Idempotent processing: If same batch_id processed, return cached result
- Deduplication: Check if meal logged today with exact same items

Code:
```python
batch_id = uuid.uuid4()
batch_state = {
    "id": batch_id,
    "items": ["2 eggs"],
    "created_at": time.time()
}

# When processing
if db.batches.find_one({"id": batch_id, "status": "processed"}):
    # Already processed, return cached result
    return db.batches.find_one({"id": batch_id})["result"]

# Process new batch
result = await process_batch(batch_state)
db.batches.insert({"id": batch_id, "status": "processed", "result": result})
```

---

### **BUG 3: Sentiment False Positive (Detecting Crisis When User Just Joking)**

```
Root Cause:
- User: "This pizza is so good, I could eat 1000 of them!" (joking, using hyperbole)
- Sentiment detector sees "1000" (high number) and "eat all" → mistakenly flags as binge alert
- Or user says "I'm dying for that burger" (expression, not literal) → flagged as crisis

Symptoms:
- Inappropriate escalation
- User offers false negative feedback
- Loss of trust in system

Solution:
- Multi-factor sentiment analysis:
  - Check for hyperbole indicators ("so good", "amazing", "love")
  - Check for idiom patterns ("dying for", "kill for")
  - Require multiple crisis keywords (not just one)
  - Check context: positivity in message > negativity

Code:
```python
def detect_crisis(message: str) -> bool:
    crisis_keywords = ["kill myself", "end my life", "suicide", "worthless", "no point"]
    hyperbole_modifiers = ["so", "really", "absolutely", "literally", "dying for", "kill for"]
    
    # Count exact crisis phrases (high confidence)
    crisis_count = sum(1 for keyword in crisis_keywords if keyword in message.lower())
    
    if crisis_count >= 2:  # Multiple crisis keywords = likely real
        return True
    
    if crisis_count == 1:
        # Check if negated or part of expression
        if any(mod in message.lower() for mod in hyperbole_modifiers):
            return False  # Likely joking
        return True
    
    return False
```

---

### **BUG 4: Batch Processing Fails Mid-Batch**

```
Root Cause:
- Batch collected: ["2 eggs", "toast", "OJ"]
- Processing start: Query USDA for "eggs" ✅
- Processing step 2: Query USDA for "toast" → API ERROR ❌
- Processing step 3: Query USDA for "OJ" → Never reached
- Result: Incomplete batch, unclear state

Symptoms:
- Partial data logged
- User confused about what was stored
- Streaks affected (was meal logged or not?)

Solution:
- All-or-nothing: If any item fails, roll back entire batch
- Clear error message: "Couldn't process 1 item. Log individually?"
- Option to retry whole batch or process individually

Code:
```python
async def process_meal_batch(items: List[str]) -> Dict:
    nutrition_results = []
    
    # Process all items first (don't update state yet)
    for item in items:
        try:
            result = await lookup_nutrition(item, timeout=5)
            if result["status"] != "success":
                # Any failure = entire batch fails
                return {
                    "status": "batch_failed",
                    "failed_item": item,
                    "message": f"Couldn't look up nutrition for '{item}'",
                    "options": ["Retry batch", "Log individually", "Manual entry"]
                }
            nutrition_results.append(result)
        except Exception as e:
            return {
                "status": "batch_failed",
                "error": str(e),
                "options": ["Retry batch", "Log individually"]
            }
    
    # All successful, now update state
    total_cal = sum(r["calories"] for r in nutrition_results)
    total_protein = sum(r["protein"] for r in nutrition_results)
    
    store_meal({"items": items, "calories": total_cal, "protein": total_protein})
    
    return {
        "status": "success",
        "items": nutrition_results,
        "totals": {"calories": total_cal, "protein": total_protein}
    }
```

---

### **BUG 5: Nudge Agent Sends Duplicate Messages**

```
Root Cause:
- APScheduler job runs at 07:00
- System time skew causes job to run again at 07:00 (duplicate execution)
- OR scheduler restarted mid-execution
- Both executions send same nudge

Symptoms:
- User receives 2-3 identical morning nudges
- User frustrated by spam

Solution:
- Idempotency key: Each nudge has unique ID
- Check if already sent before sending
- Single-execution guarantee: Job.replace_existing=True

Code:
```python
async def send_morning_nudge(user_id: str):
    # Generate unique ID for this nudge (user + timestamp)
    nudge_id = f"{user_id}_morning_{date.today()}"
    
    # Check if already sent
    if db.nudges.find_one({"nudge_id": nudge_id, "sent": True}):
        logger.info(f"Nudge {nudge_id} already sent, skipping")
        return
    
    # Send nudge
    message = generate_nudge(user_id, "morning")
    await telegram_bot.send_message(user_id, message)
    
    # Mark as sent
    db.nudges.insert({
        "nudge_id": nudge_id,
        "user_id": user_id,
        "sent": True,
        "sent_at": datetime.now()
    })

# Register job with replace_existing
scheduler.add_job(
    send_morning_nudge,
    CronTrigger(hour=7, minute=0),
    id="nudge_morning",
    replace_existing=True  # ← Important
)
```

---

## Recovery Strategies

### **Recovery Strategy 1: Batch Corruption**

```
Symptom: User's batch has inconsistent data (3 eggs, 4 eggs, 3 eggs)

Recovery:
1. Detect: Duplicate or contradictory items
2. Ask user: "I see multiple egg entries. Which is correct?"
3. User selects
4. Rebuild batch with clean data
5. Process successfully
```

### **Recovery Strategy 2: Session Loss**

```
Symptom: User reconnects, batch lost, streak affected

Recovery:
1. Check if session exists in database
2. If yes: Restore from backup
3. If no: Check if batch committed to permanent storage
4. If committed: Restore from log
5. If not: Apologize, ask to re-log items
6. Compensate: Give "bonus" log if within 1 hour of crash
```

### **Recovery Strategy 3: API Cascade Failure**

```
Symptom: USDA API, Nutritionix API, and local DB all fail

Recovery:
1. Level 1: USDA (5 sec timeout)
2. Level 2: Nutritionix (3 sec timeout)
3. Level 3: Local DB (instant)
4. Level 4: Ask user manually ("Estimate calories?")
5. Level 5: Store with 0 confidence, flag for manual review
```

---

## Testing Scenarios

### **TEST SUITE 1: Happy Path (Everything Works)**

```
Test Case: Complete morning to evening logging
1. User wakes up, gets morning nudge ✅
2. Logs breakfast (eggs, toast, OJ) ✅
3. Gets confirmation, sees calorie budget ✅
4. Logs 10 AM snack (apple) ✅
5. Logs lunch (chicken, rice) ✅
6. Logs workout (squats, pull-ups) ✅
7. Logs water (8 glasses throughout day) ✅
8. Logs sleep (previous night: 8 hours, quality 8/10) ✅
9. Logs steps (12,000) ✅
10. Views daily stats: all green ✅
11. Views weekly report Sunday: hero stat awarded ✅
12. Streak remains intact ✅

Expected Result: ✅ PASS
All data logged, streak maintained, user satisfied
```

### **TEST SUITE 2: Error Recovery**

```
Test Case: API fails, user recovers
1. User logs "2 eggs"
2. USDA API times out (>5 sec)
3. Bot switches to Nutritionix ✅
4. Nutritionix returns data ✅
5. Meal logged with "medium confidence" flag ✅

Expected Result: ✅ PASS
Graceful fallback, meal still logged
```

### **TEST SUITE 3: Edge Cases**

```
Test Case: Negative value + Impossible value
1. User: "Ate -500 calories"
2. Bot: "Calories can't be negative. Did you mean +500?"
3. User: "Yes"
4. Bot: "Adding 500 cal to meal"
5. Meal logged successfully

Expected Result: ✅ PASS
Validation caught error, user clarified, recovered
```

### **TEST SUITE 4: Batch Timeout**

```
Test Case: User starts batch, goes AFK for 20 min
1. User: "Had 2 eggs"
2. Bot: "Anything else?"
3. User doesn't respond for 20 min
4. User: "I also had toast"
5. Bot: "Your previous batch expired. Is 'toast' a new meal or part of breakfast?"
6. User: "Part of breakfast with the eggs"
7. Bot: "Got it, processing together: eggs + toast"
8. Meal logged ✅

Expected Result: ✅ PASS
Batch recovered despite timeout, user satisfied
```

### **TEST SUITE 5: Emotional Crisis Detection**

```
Test Case: User expressing guilt/shame
1. User: "Ugh I'm so fat. Had 500 calories just for lunch 😞"
2. Sentiment: -0.7 (negative)
3. Bot: Still logs 500 cal ✅
4. Bot Response: "I hear you're being hard on yourself. 500 cal for lunch is totally normal! You're doing great. 💪"
5. Offers support option ✅

Expected Result: ✅ PASS
Meal logged, emotional support provided, no judgment
```

---

## Summary: Critical User Journeys

| Journey | Priority | Likelihood | Risk |
|---------|----------|-----------|------|
| Happy path (all logging works) | MUST | 70% | Low |
| Batch timeout (user AFK) | SHOULD | 40% | Medium |
| API failure (USDA down) | SHOULD | 10% | High |
| Negative values (data validation) | MUST | 5% | High |
| Session crash/recovery | SHOULD | 15% | High |
| Emotional crisis detection | MUST | 5% | Critical |
| Multi-item batch collection | MUST | 80% | Low |
| Nudge spam (duplicates) | SHOULD | 2% | Medium |
| Timezone change | SHOULD | 20% | Medium |
| Data duplication | SHOULD | 3% | High |

---

**Document Status:** ✅ Complete  
**Created:** November 16, 2025  
**Total User Stories:** 18 (core) + 5 (nudge) + 3 (batch) = 26  
**Edge Cases Identified:** 50+  
**Critical Bugs Documented:** 5  
**Recovery Strategies:** 3  
**Test Suites:** 5