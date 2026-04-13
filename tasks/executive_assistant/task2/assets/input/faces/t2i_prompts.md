# T2I & Video Generation Prompts — Task 2

All files go into:
```
tasks/task2-Intercity-interview-scheduling-and-candidate-identity-verification/input/
```

---

## IMAGES (google/gemini-3.1-flash-image-preview)

Recommended size: 512×512 or 768×768. Save as JPG.

---

### `input/faces/C01_face.jpg`
```
Professional headshot portrait photo. East Asian man, early thirties, short neat black hair, neutral confident expression, white collared shirt, plain light gray background, passport photo style, sharp focus, photorealistic.
```

---

### `input/faces/C02_face_id.jpg` ⚠️ TRAP — must look clearly different from C02_face_video.jpg
```
Professional ID card headshot portrait photo. East Asian woman, late twenties, distinctly LONG and NARROW oval face shape, very long straight jet-black hair hanging well past the shoulders, formal white blouse, plain light background, neutral expression, passport photo style, photorealistic. Emphasize: face is noticeably long and narrow (tall oval), hair is long and straight past shoulders.
```

---

### `input/faces/C02_face_video.jpg` ⚠️ TRAP — must look clearly different from C02_face_id.jpg
```
Casual portrait photo as if captured from a video call. East Asian woman, late twenties, distinctly ROUND full face (circular face shape), SHORT dark hair cut just above the ears, casual top, home office background, looking directly at camera, natural light. Emphasize: face is very round (circular), hair is SHORT above the ears. Photorealistic.
```

---

### `input/faces/C02_selfie.jpg`
```
Smartphone selfie photo. East Asian woman, late twenties, ROUND face, SHORT dark hair above the ears, casual outfit, warm indoor background, slight smile, natural selfie angle. Photorealistic.
```

---

### `input/faces/C03_face.jpg`
```
Professional headshot portrait photo. East Asian man, early thirties, short black hair, slight friendly smile, dark navy collared shirt, plain light background, passport photo style, photorealistic.
```

---

### `input/faces/C04_face.jpg`
```
Professional headshot portrait photo. East Asian woman, mid-twenties, medium-length straight black hair to shoulders, neat neutral expression, white blouse, plain light gray background, passport photo style, photorealistic.
```

---

### `input/faces/C05_face.jpg`
```
Professional headshot portrait photo. East Asian woman, late twenties, short black bob haircut at jaw level, calm neutral expression, dark blazer, plain light background, passport photo style, photorealistic.
```

---

### `input/faces/C06_face.jpg` ⚠️ Must have WHITE shirt — PIL darkens it to gray for post-splice frames
```
Professional headshot portrait photo. East Asian man, mid-thirties, short black hair with slight gray at temples, confident expression, WHITE dress shirt (clearly white), plain light background, passport photo style, sharp clear image, photorealistic.
```

---

### `input/faces/C07_face.jpg`
```
Professional headshot portrait photo. Young East Asian woman, mid-twenties, long straight black hair, bright friendly expression, white blouse, plain light gray background, passport photo style, photorealistic.
```

---

### `input/faces/C08_face.jpg`
```
Professional headshot portrait photo. East Asian man, early thirties, short neat black hair, professional serious expression, navy blue collared shirt, plain light gray background, passport photo style, photorealistic.
```

---

## SELF-INTRO PHOTOS — `input/faces/` (nano banana2)

These are the `self_intro.jpg` portrait photos (one per candidate).
Save to `input/faces/` — the face composite script will embed them into the final `input/C0X_self_intro.jpg`.
Recommended size: 512×512 or 768×512.

> **Note**: C01/C03/C04/C05/C07/C08 self_intro faces are the same as their `_face.jpg` files.
> You do NOT need to generate separate images — the script reuses `CXX_face.jpg` for those.
> Only C02 needs a separate face image (`C02_face_video.jpg`), and C06's composite effect is done by PIL.

No additional t2i images needed beyond the 10 face images above.

---

## After saving all face images to `input/faces/`, run:

```bash
python3 scripts/generate_task2_images_face.py
```

This generates:
- `input/C01–C08_id_photo.jpg` (8 ID card photos)
- `input/C01–C08_resume_scan.jpg` (8 resume scans)
- `input/C01–C08_self_intro.jpg` (8 self-intro portraits; C06 gets PIL composite splice effect)
- `input/C02_recent_selfie.jpg`
