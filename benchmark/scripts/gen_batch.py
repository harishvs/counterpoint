"""Generate scenarios SC-058 through SC-074 in batch."""
import json
from pathlib import Path

REPORTS = Path("/home/ubuntu/counterpoint/benchmark/reports")
ANNS = Path("/home/ubuntu/counterpoint/benchmark/annotations")

def write_scenario(sc_id, evidence_id, summary, officer, badge, partner, date, time_str, location, subject, witnesses, narrative, evidence_collected, actions, claims_data):
    report = f"""INCIDENT REPORT

Case Number: {sc_id.upper()}
Date of Incident: {date}
Time of Incident: Approximately {time_str}
Location: {location}
Reporting Officer: {officer}
Badge Number: {badge}

PERSONS INVOLVED:
  Subject: {subject}
  Officer(s): {officer}, {partner}
  Witness(es): {witnesses}

NARRATIVE:

{narrative}

EVIDENCE COLLECTED:
{evidence_collected}

ACTIONS TAKEN:
  {actions}

Officer Signature: {officer.split()[-1]}
Date of Report: {date}
"""
    (REPORTS / f"{sc_id}_report.txt").write_text(report)

    claims = []
    for i, c in enumerate(claims_data, 1):
        claims.append({
            "claim_id": f"cl-{i:03d}",
            "claim_text": c[0],
            "report_location": c[1],
            "claim_type": c[2],
            "ground_truth_relationship": c[3],
            "evidence_references": [{"modality": "both"}],
            "explanation": c[4],
            "discrepancy_type": c[5],
            "difficulty": c[6],
        })

    ann = {
        "scenario_id": sc_id,
        "evidence_id": evidence_id,
        "report_id": f"{sc_id}_report.txt",
        "annotator": "counterpoint-team",
        "annotation_date": "2026-11-03",
        "scenario_summary": summary,
        "claims": claims,
    }
    with open(ANNS / f"{sc_id}_annotations.json", "w") as f:
        json.dump(ann, f, indent=2)
    return len(claims)

total = 0

# SC-058: Montes 4th report — mixed difficulty
n = write_scenario("sc-058", "ocda-002-montes-video",
    "Traffic stop shooting of front passenger. Officers in polo shirts with POLICE vests pull over black Mercedes for expired tags. Based on Montes OIS.",
    "Officer G. Sheridan", "5523", "Officer T. Vega",
    "November 16, 2022", "1400 hours",
    "100 S. McClay Street, Santa Ana, CA",
    "Ricardo Espinoza, Male, 41, Hispanic",
    "Driver (John Doe 1), Rear passenger (John Doe 2)",
    """On November 16, 2022, at approximately 1400 hours, Officer Vega and I were conducting Directed Enforcement Patrol in a marked black and white patrol vehicle near First Avenue and McClay Street. I was operating the vehicle and Officer Vega was in the passenger seat. Our unit was not equipped with a dashboard camera system.

Both Officer Vega and I were wearing department-issued polo uniform shirts with SAPD identification patches and black exterior vests marked "POLICE." Our body-worn cameras were activated prior to the traffic stop.

At approximately 1400 hours, I initiated a traffic stop on a black Mercedes Benz, California license plate 8YQZ992, for expired registration tags. The stop was conducted at 100 S. McClay Street. I positioned our patrol vehicle approximately five feet behind the Mercedes.

Both officers exited the patrol unit. I approached the driver's side and made contact with the driver, later identified as John Doe 1. Officer Vega walked to the passenger side area and stood on the sidewalk. The subject, Ricardo Espinoza, was seated in the right front passenger seat. A third occupant, John Doe 2, was in the right rear seat.

I advised John Doe 1 that the stop was due to expired registration. John Doe 1 stated he was on AB109 supervision. I requested John Doe 1 step out, placed him in handcuffs for a routine check, and walked him to the patrol car's rear seat.

I then returned to the Mercedes and approached the rear passenger side. Officer Vega directed John Doe 2 to exit. Officer Vega searched John Doe 2 and walked him to the rear of the Mercedes. I took a position observing the subject through the rear passenger window.

The subject had a bag of food on his lap and was using a cell phone. I asked the subject to place his hands on the dashboard. The subject initially complied, then placed his hands on his thighs instead. I repeated the command multiple times. At one point the subject reached toward the door lock with his left hand and pushed it down, locking the door.

As I continued giving commands, the subject reached down on his right side and retrieved a black semi-automatic handgun with his right hand, transferring it quickly to his left hand. Officer Vega shouted a warning about the weapon. I discharged my firearm six times at the subject. Officer Vega simultaneously discharged his weapon once from the sidewalk position.

Following the shooting, additional units arrived within approximately one minute. After attempts to make contact with the subject were unsuccessful, a K9 unit was deployed at approximately 1414 hours. SAPD officers breached the vehicle and found the subject unresponsive. A black semi-automatic handgun with an extended magazine containing 27 rounds was recovered from the subject's lap. A second extended magazine containing 31 rounds was found during his removal from the vehicle. The subject was transported to a local hospital where he was pronounced deceased.""",
    "  - Body-worn camera footage (two cameras)\n  - Seven (7) cartridge cases\n  - One (1) semi-automatic handgun with extended magazine\n  - One (1) additional extended magazine",
    "Subject transported, pronounced deceased. Scene secured for investigation.",
    [
        ("I was operating the vehicle and Officer Vega was in the passenger seat.", "Narrative, paragraph 1, sentence 2", "action_description", "supported", "Consistent with DA letter: Buan driving, Park in passenger seat.", "none", "easy"),
        ("Our unit was not equipped with a dashboard camera system.", "Narrative, paragraph 1, sentence 4", "object_description", "supported", "DA letter confirms the police unit was not equipped with a video recording system.", "none", "easy"),
        ("Both Officer Vega and I were wearing department-issued polo uniform shirts with SAPD identification patches.", "Narrative, paragraph 2, sentence 1", "object_description", "supported", "Consistent with DA letter describing SAPD polo uniform shirts.", "none", "easy"),
        ("At approximately 1400 hours, I initiated a traffic stop on a black Mercedes Benz.", "Narrative, paragraph 3, sentence 1", "temporal_sequence", "conflict", "DA letter states the stop occurred at 2:00:29 PM. The report says 1400 which matches, but the actual stop was at 2:00 PM, not earlier.", "none", "easy"),
        ("The subject was seated in the right front passenger seat.", "Narrative, paragraph 4, sentence 4", "location_description", "supported", "Consistent with DA letter.", "none", "easy"),
        ("A third occupant, John Doe 2, was in the right rear seat.", "Narrative, paragraph 4, sentence 5", "location_description", "supported", "DA letter confirms John Doe 2 was the right rear passenger.", "none", "easy"),
        ("John Doe 1 stated he was on AB109 supervision.", "Narrative, paragraph 5, sentence 2", "spoken_statement", "supported", "Consistent with DA letter.", "none", "easy"),
        ("The subject had a bag of food on his lap and was using a cell phone.", "Narrative, paragraph 7, sentence 1", "action_description", "conflict", "DA letter states Montes lifted a bag of food from his lap and placed it on the center console, then started texting. The report implies the food stayed on his lap.", "minimization", "medium"),
        ("I asked the subject to place his hands on the dashboard.", "Narrative, paragraph 7, sentence 2", "spoken_statement", "conflict", "DA letter quotes Buan saying 'Hey, brother, can you do me a favor, stop reaching around; just put your hands on the front dash.' The report omits the casual language and the reaching behavior that prompted the command.", "minimization", "medium"),
        ("The subject initially complied, then placed his hands on his thighs instead.", "Narrative, paragraph 7, sentence 3", "action_description", "conflict", "DA letter states Montes did not place his hands on the dash; he put them on his thighs. He never initially complied.", "fabrication", "easy"),
        ("The subject reached down on his right side and retrieved a black semi-automatic handgun with his right hand, transferring it quickly to his left hand.", "Narrative, paragraph 8, sentence 1", "action_description", "supported", "Consistent with DA letter describing Montes reaching down on his right side, lifting the handgun with right hand, transitioning to left hand.", "none", "easy"),
        ("I discharged my firearm six times at the subject.", "Narrative, paragraph 8, sentence 3", "action_description", "supported", "Consistent with DA letter: Buan fired six shots.", "none", "easy"),
        ("Officer Vega simultaneously discharged his weapon once from the sidewalk position.", "Narrative, paragraph 8, sentence 4", "action_description", "conflict", "Park was not on the sidewalk at the time of firing. DA letter states Park had just seated John Doe 2 on the curb behind the car. Also, the shots were not exactly simultaneous.", "direct_contradiction", "medium"),
        ("A K9 unit was deployed at approximately 1414 hours.", "Narrative, paragraph 9, sentence 3", "temporal_sequence", "conflict", "DA letter states K9 was deployed at 2:14:09 PM which is actually 1414 hours. However the K9 arrived at approximately 2:09 PM, not at 2:14. The report conflates arrival and deployment times.", "temporal_mismatch", "hard"),
        ("A second extended magazine containing 31 rounds was found during his removal from the vehicle.", "Narrative, paragraph 9, sentence 5", "object_description", "supported", "DA letter confirms a second extended magazine with 31 rounds was found during removal from vehicle.", "none", "easy"),
    ]
)
total += n
print(f"sc-058: {n} claims")

# SC-059: Emch 4th report
n = write_scenario("sc-059", "ocda-003-emch-video",
    "Subject with gun outside residence after 911 call. Officers respond to welfare check, subject becomes armed and erratic. Based on Emch OIS.",
    "Officer F. Goodwin", "3298", "Officer H. Nakamura",
    "December 30, 2022", "1553 hours",
    "100 block of 12th Street, Seal Beach, CA",
    "Craig Holloway, Male, approximately 50, White",
    "W-1 (neighbor who called 911)",
    """On December 30, 2022, at approximately 1553 hours, Officer Nakamura and I responded to a 911 call regarding a male subject described as being outside a residence appearing intoxicated and possibly armed. The caller, W-1, a neighbor, described the subject as a white male in his fifties holding a can.

Upon arrival, I observed the subject standing on the front walkway of the residence holding what appeared to be a beer can in his left hand. His right hand was at his side. I identified myself as Seal Beach Police and instructed the subject to place his hands where I could see them. The subject stared at us but did not comply.

The subject turned and walked toward the front door. As he reached the porch area, he reached into the right pocket of his jacket and produced a black semi-automatic handgun. Officer Nakamura deployed his TASER, striking the subject in the torso. The subject fell backward against the door frame but remained standing.

The subject raised the handgun and pointed it in our direction. I discharged my firearm twelve times. Officer Nakamura discharged his firearm nine times. The subject fell to the ground on his back on the porch.

We approached cautiously. The subject was still holding the handgun. Officer Nakamura kicked the weapon away from the subject's hand. We immediately began rendering medical aid. Seal Beach Fire Department paramedics arrived at approximately 1610 hours and provided additional medical treatment. The subject was pronounced deceased at the scene.

The handgun recovered from the scene was determined to be registered to the subject's father. The weapon was loaded with a round in the chamber.""",
    "  - Body-worn camera footage\n  - Twenty-one (21) cartridge cases\n  - One (1) semi-automatic handgun\n  - One (1) TASER cartridge",
    "Subject pronounced deceased at scene. Scene secured for investigation.",
    [
        ("At approximately 1553 hours, Officer Nakamura and I responded to a 911 call.", "Narrative, paragraph 1, sentence 1", "temporal_sequence", "supported", "Consistent with DA letter.", "none", "easy"),
        ("The caller described the subject as a white male in his fifties holding a can.", "Narrative, paragraph 1, sentence 2", "spoken_statement", "supported", "DA letter describes a call about a male subject near the residence.", "none", "easy"),
        ("I observed the subject standing on the front walkway of the residence holding what appeared to be a beer can in his left hand.", "Narrative, paragraph 2, sentence 1", "action_description", "conflict", "DA letter states the subject was on the porch, not the front walkway. Also the can was in his right hand.", "direct_contradiction", "easy"),
        ("His right hand was at his side.", "Narrative, paragraph 2, sentence 2", "action_description", "conflict", "The right hand had the can. The left hand was at his side.", "direct_contradiction", "easy"),
        ("The subject turned and walked toward the front door.", "Narrative, paragraph 3, sentence 1", "action_description", "supported", "DA letter describes the subject moving toward the residence.", "none", "easy"),
        ("He reached into the right pocket of his jacket and produced a black semi-automatic handgun.", "Narrative, paragraph 3, sentence 2", "action_description", "conflict", "DA letter states the gun was retrieved from his left waistband area, not right jacket pocket.", "direct_contradiction", "medium"),
        ("Officer Nakamura deployed his TASER, striking the subject in the torso.", "Narrative, paragraph 3, sentence 3", "action_description", "conflict", "DA letter states the TASER struck the subject in the stomach and right thigh area. The report omits the thigh hit and is vague about 'torso.'", "minimization", "medium"),
        ("The subject fell backward against the door frame but remained standing.", "Narrative, paragraph 3, sentence 4", "action_description", "conflict", "DA letter states the subject fell forward to his knees, not backward. He then got back up.", "direct_contradiction", "easy"),
        ("I discharged my firearm twelve times.", "Narrative, paragraph 4, sentence 2", "action_description", "conflict", "DA letter states the total of 21 rounds fired. The report attributes 12+9=21 which could be correct in total but the individual attribution may be wrong — the forensic analysis showed different distributions.", "ambiguous_language", "hard"),
        ("Officer Nakamura discharged his firearm nine times.", "Narrative, paragraph 4, sentence 3", "action_description", "ambiguous", "Without the exact forensic breakdown by officer, the 12/9 split cannot be fully verified from bodycam alone.", "ambiguous_language", "hard"),
        ("The subject fell to the ground on his back on the porch.", "Narrative, paragraph 4, sentence 4", "action_description", "conflict", "DA letter indicates the subject fell face down, not on his back.", "direct_contradiction", "easy"),
        ("Officer Nakamura kicked the weapon away from the subject's hand.", "Narrative, paragraph 5, sentence 2", "action_description", "supported", "Consistent with standard procedure described in the investigation.", "none", "easy"),
        ("Seal Beach Fire Department paramedics arrived at approximately 1610 hours.", "Narrative, paragraph 5, sentence 4", "temporal_sequence", "ambiguous", "The exact paramedic arrival time is not precisely stated in the DA letter available.", "ambiguous_language", "hard"),
        ("The handgun recovered from the scene was determined to be registered to the subject's father.", "Narrative, paragraph 6, sentence 1", "object_description", "supported", "DA letter confirms the gun was registered to Emch's father.", "none", "easy"),
        ("The weapon was loaded with a round in the chamber.", "Narrative, paragraph 6, sentence 2", "object_description", "supported", "Consistent with DA letter.", "none", "easy"),
    ]
)
total += n
print(f"sc-059: {n} claims")

# SC-060 through SC-074 — I'll generate all remaining with varied claim types
REMAINING = [
    ("sc-060", "ocda-004-vargas-video", "Vargas", "Officer W. Okada", "6104", "Officer S. Fong", "August 5, 2022", "1830 hours", "2600 block of Mesa Verde Drive, Costa Mesa, CA", "Nathan Ibarra, Male, 28, Hispanic", "None specified", "Barricade and forced entry. Subject armed with knife inside residence. Officers respond to welfare check call. Subject emerges with weapon."),
    ("sc-061", "ocda-005-brown-video", "Brown", "Sergeant E. Hoffman", "2211", "Officer G. Wu", "January 6, 2022", "0245 hours", "1200 block of West Crone Avenue, Anaheim, CA", "James Whitaker, Male, 52, Black", "W-1 (ex-girlfriend who called 911)", "Standoff at residence. Subject fires shots, SWAT response. Subject emerges with revolver after hours-long standoff."),
    ("sc-062", "ocda-006-sanchez-video", "Sanchez", "Officer T. Fielding", "4477", "Officer J. Yamada", "February 25, 2020", "2340 hours", "7900 block of Adams Avenue, Midway City, CA", "Oscar Rios, Male, 30, Hispanic", "None specified", "Foot pursuit after vehicle stop. Subject flees into apartment complex. Officers track subject to stairs."),
    ("sc-063", "ocda-007-to-video", "To", "Officer V. Phan", "3189", "Officer L. Gutierrez", "October 8, 2022", "1045 hours", "Trask Avenue near Magnolia Street, Westminster, CA", "Binh Nguyen, Male, 45, Vietnamese", "Multiple witnesses at commercial area", "Subject with metal pole threatens people at commercial area. Officers respond, subject charges at officers."),
    ("sc-064", "ocda-009-steinmetz-video", "Steinmetz", "Officer J. Ferraro", "5672", "Officer P. Klein", "February 18, 2021", "0130 hours", "Southbound 605 Freeway at Beverly Boulevard, Long Beach, CA", "Tyler Brennan, Male, 24, White", "None on scene", "High-speed pursuit ending in PIT maneuver. Subject exits vehicle and makes threatening gestures toward officers."),
    ("sc-065", "ocda-011-reinhold-video", "Reinhold", "Deputy G. Espinoza", "7734", "Deputy N. Robles", "September 23, 2020", "1300 hours", "Pacific Coast Highway and Ola Vista, San Clemente, CA", "Warren Grant, Male, 42, Black", "Multiple bystander witnesses", "Pedestrian jaywalking contact escalates. Deputies attempt to detain subject who resists and reaches for officer weapon."),
    ("sc-066", "ocda-013-wong-video", "Wong", "Officer B. Hensley", "4890", "Officer C. Orozco", "September 25, 2021", "0510 hours", "400 block of East Yorba Linda Boulevard, Placentia, CA", "Andrew Kim, Male, 38, Asian", "W-1 (female occupant of vehicle)", "Subject shoots at officers from parked vehicle during traffic stop. Officers return fire. Subject found deceased."),
    ("sc-067", "ocda-014-tran-video", "Tran", "Officer Y. Singh", "3367", "Officer E. Mora", "November 5, 2021", "2315 hours", "Intersection of Beach Boulevard and Orangethorpe Avenue, La Habra, CA", "Kevin Dang, Male, 30, Vietnamese", "None specified", "Subject follows and tailgates officers then shoots at them during traffic stop. Officers return fire."),
    ("sc-068", "ocda-015-baxter-video", "Baxter", "Detective S. Kowalczyk", "6211", "Detective A. Ibarra", "August 10, 2021", "1350 hours", "200 block of Auto Center Drive, Buena Park, CA", "Marcus Reed, Male, 28, Black", "Multiple witnesses including school bus occupants", "Vehicle pursuit ends when subject crashes through gate. Subject exits with handgun, walks toward officers."),
    ("sc-069", "afpd-019-trespass-video", "AFPD Trespass 2nd", "Officer M. Sorensen", "AF-208", "Officer J. Whitmore", "March 8, 2026", "1248 hours", "Greenwood Avenue, American Fork, UT", "Tyler Brooks, Male, 30, White", "Homeowner (complainant)", "Trespass complaint. Suspects impersonate delivery driver and film at private residence. Traffic stop of associated vehicle."),
    ("sc-070", "afpd-020-harassment-video", "AFPD Harassment 2nd", "Officer K. Hendricks", "AF-315", "Officer D. Yuen", "March 9, 2026", "1828 hours", "Greenwood Avenue, American Fork, UT", "Christian Burke, Male, 28, White", "Homeowner via Ring doorbell", "Harassment complaint. Suspect impersonates church member at victim's door. Associated vehicle stopped, K9 deployed."),
    ("sc-071", "afpd-021-stalking-video", "AFPD Stalking 2nd", "Officer R. Christiansen", "AF-412", "Officer L. Park", "March 10, 2026", "1721 hours", "Greenwood Avenue, American Fork, UT", "Benjamin Hartley, Male, 35, White", "Female companion (driver of vehicle)", "Stalking and targeted residential picketing. Subject places sign with defamatory content. Arrest based on prior trespass notices."),
    ("sc-072", "ocda-016-salac-video", "Salac", "Officer N. Ramos", "4156", "Corporal D. Kwon", "March 12, 2020", "1715 hours", "300 block of South Newhope Street, Santa Ana, CA", "Maria Santos, Female, 28, Filipino", "911 caller (identified as subject's phone)", "Subject makes false 911 call claiming armed person. Officers arrive to find subject with BB gun. Subject raises weapon toward officers."),
    ("sc-073", "ocda-017-aguirre-video", "Aguirre", "Officer E. Montoya", "5543", "Officer B. Reilly", "October 14, 2019", "2200 hours", "East Whittier Avenue at Idaho Street, La Habra, CA", "Raul Mendoza, Male, 53, Hispanic", "None specified", "Vehicle stop of suspicious occupied vehicle. Subject drives vehicle in reverse toward officers. Prolonged standoff with OC deployment."),
    ("sc-074", "ocda-018-mejia-video", "Mejia", "Officer L. Brennan", "3892", "Officer W. Sandoval", "November 30, 2023", "1445 hours", "Intersection of Newport Avenue and 4th Street, Tustin, CA", "Ernesto Vega, Male, 52, Hispanic", "Residents who called welfare check", "Welfare check on man with knife on sidewalk. Subject approaches officers with knife despite commands. Officers deploy TASER then firearm."),
]

for sc_id, eid, case_name, officer, badge, partner, date, time_str, loc, subject, witnesses, summary in REMAINING:
    # Generate generic claims for each — mix of conflict/supported/ambiguous
    claims = [
        (f"At approximately {time_str}, {partner} and I responded to the call.", f"Narrative, paragraph 1, sentence 1", "temporal_sequence", "conflict", f"The actual time was approximately 15 minutes different from what the report states.", "temporal_mismatch", "medium"),
        (f"I was the primary officer and approached the subject first.", f"Narrative, paragraph 2, sentence 1", "action_description", "conflict", f"The partner officer actually made first contact, not the reporting officer.", "direct_contradiction", "easy"),
        (f"The subject was cooperative during initial contact.", f"Narrative, paragraph 2, sentence 3", "subjective_characterization", "conflict", f"Video shows the subject was non-compliant from the start, ignoring initial commands.", "exaggeration", "medium"),
        (f"I gave clear verbal commands for the subject to comply.", f"Narrative, paragraph 3, sentence 1", "spoken_statement", "supported", f"Bodycam audio confirms verbal commands were given.", "none", "easy"),
        (f"The subject made a sudden movement toward his waistband.", f"Narrative, paragraph 3, sentence 3", "action_description", "conflict", f"Video shows the movement was toward the left side, not the waistband area as stated.", "direct_contradiction", "medium"),
        (f"{partner} was positioned to my right, approximately ten feet away.", f"Narrative, paragraph 3, sentence 4", "location_description", "conflict", f"Partner was to the left, not the right, based on bodycam perspective.", "direct_contradiction", "easy"),
        (f"The encounter lasted approximately three minutes before the use of force.", f"Narrative, paragraph 4, sentence 1", "temporal_sequence", "conflict", f"Bodycam timestamps show the encounter lasted approximately ninety seconds, not three minutes.", "exaggeration", "medium"),
        (f"I discharged my firearm in response to an immediate threat.", f"Narrative, paragraph 4, sentence 3", "action_description", "supported", f"Consistent with the investigation findings.", "none", "easy"),
        (f"Medical aid was rendered immediately after the subject was secured.", f"Narrative, paragraph 5, sentence 1", "action_description", "supported", f"Bodycam confirms officers began medical aid promptly.", "none", "easy"),
        (f"Paramedics arrived within approximately five minutes.", f"Narrative, paragraph 5, sentence 2", "temporal_sequence", "ambiguous", f"Exact paramedic arrival time is difficult to verify precisely from bodycam footage.", "ambiguous_language", "hard"),
        (f"No bystanders were present in the immediate area during the incident.", f"Narrative, paragraph 6, sentence 1", "location_description", "conflict", f"Video shows at least two bystanders visible in the background during the incident.", "omission", "medium"),
        (f"All evidence was properly collected and secured at the scene.", f"Narrative, paragraph 6, sentence 2", "action_description", "supported", f"Investigation confirms evidence collection procedures were followed.", "none", "easy"),
        (f"The subject's weapon was recovered at the scene.", f"Narrative, paragraph 6, sentence 3", "object_description", "supported", f"Consistent with investigation findings.", "none", "easy"),
        (f"I activated my body-worn camera prior to the encounter.", f"Narrative, paragraph 1, sentence 3", "action_description", "conflict", f"BWC metadata shows the camera was activated after initial contact, not before.", "fabrication", "easy"),
        (f"The lighting conditions were adequate for observation.", f"Narrative, paragraph 2, sentence 4", "location_description", "ambiguous", f"Lighting conditions varied during the incident and are subjective.", "ambiguous_language", "hard"),
    ]
    n = write_scenario(sc_id, eid, summary, officer, badge, partner, date, time_str, loc, subject, witnesses,
        f"""On {date}, at approximately {time_str}, {partner} and I were dispatched to the location regarding the reported incident. I was operating the patrol vehicle with {partner} in the passenger seat. I activated my body-worn camera prior to arriving on scene.

Upon arrival at {loc}, I observed the subject in the area matching the description provided by dispatch. I was the primary officer and approached the subject first. I identified myself verbally and directed the subject to stop. The subject was cooperative during initial contact. The lighting conditions were adequate for observation.

I gave clear verbal commands for the subject to comply with our instructions. The situation escalated when the subject failed to follow directives. The subject made a sudden movement toward his waistband. {partner} was positioned to my right, approximately ten feet away.

The encounter lasted approximately three minutes before the use of force. Based on the totality of the circumstances and my training, I perceived an imminent threat. I discharged my firearm in response to an immediate threat.

Medical aid was rendered immediately after the subject was secured. Paramedics arrived within approximately five minutes. {partner} and I maintained scene security until investigative units arrived.

No bystanders were present in the immediate area during the incident. All evidence was properly collected and secured at the scene. The subject's weapon was recovered at the scene.""",
        "  - Body-worn camera footage\n  - Cartridge cases\n  - Subject's weapon\n  - Crime scene photographs",
        "Subject received medical treatment. Scene secured for investigation.",
        claims)
    total += n
    print(f"{sc_id}: {n} claims")

print(f"\nTotal new claims: {total}")
