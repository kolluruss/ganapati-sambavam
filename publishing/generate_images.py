import os
import time
import base64
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

OUTPUT_DIR = "telugu/meta_data/images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

prompts = [
    # Sarga 1
    ("sarga_01_01_himalayas.png",
     "A majestic, meditative view of the snow-capped Himalayas envisioned as a venerable, ancient Indian sage deep in meditation. The peaks glow with the golden-orange light of dawn, resembling saffron (kesar), seamlessly blending into the white snow and green valleys below, subtly evoking the Indian tricolor. Serene, hyper-detailed, spiritual atmosphere, classical Indian art style."),

    ("sarga_01_02_amarnath.png",
     "The sacred, naturally formed ice Shiva Lingam inside the mystical Amarnath cave. The translucent ice is illuminated by an ethereal, divine blue and white glowing aura. Devotees are seen faintly in the background with hands folded in deep reverence. Devotional mood, hyper-realistic, peaceful lighting."),

    # Sarga 2
    ("sarga_02_01_tapasya.png",
     "Goddess Parvati deep in austere penance (Tapasya) amidst the harsh, snowy Himalayan mountains. She is dressed in simple ascetic garments, her face calm and glowing with a profound spiritual aura, eyes gently closed. A divine, respectful, and meditative mood, rich in traditional Indian aesthetics."),

    ("sarga_02_02_wedding.png",
     "The sacred Panigrahana (wedding ritual) of Lord Shiva and Goddess Parvati. Lord Shiva, adorned with a glowing crescent moon on his matted hair, gently holds the lotus-like hand of a radiant Parvati. They are taking the Saptapadi (seven steps) around the holy, brightly glowing Agni (fire). Majestic, vibrant traditional colors, divine and joyous atmosphere."),

    # Sarga 3
    ("sarga_03_01_samadhi.png",
     "Lord Shiva sitting in a state of absolute, profound Samadhi (deep meditation) on Mount Kailash. He is seated in Padmasana on a tiger skin, eyes half-closed, a serene smile on his face, radiating tranquil cosmic energy. The six seasons are subtly manifested in the surrounding nature, serving him. Meditative, hyper-detailed, spiritual."),

    ("sarga_03_02_clay_creation.png",
     "A magical, motherly moment showing Goddess Parvati lovingly shaping a beautiful clay idol of a young boy and a small mouse. A mystical, golden glowing aura transfers from her hands into the clay figures as she breathes life into them using her Yogashakti (yogic power). Soft, warm, divine lighting."),

    # Sarga 4
    ("sarga_04_01_doorway_debate.png",
     "A brave, radiant young boy standing firmly at the ornate, stone doorway of Goddess Parvati's chambers, holding a small green bamboo stick. He courageously and respectfully blocks the path of the majestic Lord Shiva. The scene captures a tense but philosophical debate (Shastrartha). Rich classical architectural details, dramatic but respectful lighting."),

    ("sarga_04_02_parvati_grief.png",
     "A sorrowful, emotionally charged scene showing Goddess Parvati weeping over her fallen, clay-born son after Lord Shiva's trident strike. Lord Shiva stands nearby, his anger replaced by sudden realization and remorse. The mood is heavily melancholic, compassionate, and dramatic, reflecting the deep sorrow of the Divine Mother."),

    # Sarga 5
    ("sarga_05_01_elephant_head.png",
     "A profoundly divine, awe-inspiring moment where Lord Shiva, with immense compassion, places a majestic elephant calf's head onto the young boy's body. A golden, celestial light heals the connection, bringing the boy back to life as Lord Ganesha. Joyous, divine, and miraculous atmosphere."),

    ("sarga_05_02_baby_ganesha.png",
     "Baby Ganesha, with his beautiful new elephant head, happily playing in the lush, blooming gardens of Kailash. He is playfully drawing the sacred Sanskrit Om symbol in the air with his small trunk. A small mouse looks on affectionately. Cute, divine, peaceful, vibrant nature."),

    # Sarga 6
    ("sarga_06_01_parashurama_axe.png",
     "The fierce sage Parashurama, glowing with fiery anger, throws his divine axe (Parashu) towards Lord Ganesha at the gates of Kailash. Ganesha stands calmly and respectfully receives the axe on his left tusk to honor his father's weapon, causing the tusk to break. Dynamic, mythological, highly detailed, expressive."),

    ("sarga_06_02_vishnu_mediates.png",
     "Lord Vishnu appearing peacefully to mediate between Sage Parashurama and Lord Ganesha. The divine presence of Hari calms the anger, bringing harmony and teaching the non-duality of Hari and Hara. Ganesha proudly and playfully holds his broken tusk. Meditative, harmonious, spiritual lighting."),

    # Sarga 7
    ("sarga_07_01_mahabharata_writing.png",
     "Sage Vyasa, an ancient, wise ascetic with a glowing aura, sits in a serene forest ashram dictating the epic Mahabharata. Lord Ganesha sits across from him, swiftly and flawlessly writing the Sanskrit verses on palm leaves using his broken tusk as a pen. Scholarly, meditative, ancient Indian heritage."),

    ("sarga_07_02_celestial_flowers.png",
     "A celestial shower of glowing, fragrant flowers falling from the heavens over Lord Ganesha and Sage Vyasa as they successfully complete the monumental writing of the Mahabharata. The atmosphere is triumphant, divine, illuminated by golden-hour sunlight filtering through the ashram trees."),

    # Sarga 8
    ("sarga_08_01_modaka_offering.png",
     "Lord Indra and the Devas respectfully offering a giant, glowing, divine Modaka (sweet) to Lord Ganesha on his birthday. The Modaka shines with a heavenly golden aura, symbolizing the nectar of immortality. Joyous, celebratory, opulent celestial setting."),

    ("sarga_08_02_circumambulation.png",
     "Lord Ganesha cleverly and devotedly circumambulating his seated parents, Lord Shiva and Goddess Parvati, on his small mouse vehicle, recognizing them as his entire universe. In the background sky, Lord Kartikeya is seen flying away swiftly on his peacock. Heartwarming, devotional, philosophical mood."),

    # Sarga 9
    ("sarga_09_01_democratic_leader.png",
     "A metaphorical, grand representation of Lord Ganesha as the ideal, compassionate democratic leader. He is shown with large, attentive ears listening to the masses, and small, focused eyes looking at subtle details. He holds a Modaka to nourish the people and an axe to destroy corruption. Peaceful, inclusive, majestic art style."),

    ("sarga_09_02_diwali_ganesha.png",
     "Lord Ganesha's divine silhouette subtly reflecting within the vibrant, glowing diyas (oil lamps) of a Diwali celebration. In the background, the subtle imagery of Indian martyrs and Mother India is honored. A feeling of nationwide unity, joy, and secular harmony. Festive, warm, highly spiritual."),

    # Sarga 10
    ("sarga_10_01_rajasthan_gandhi.png",
     "A meditative landscape of Rajasthan showing an ancient, majestic fort bathed in the golden sunlight of dawn. In the sky above, a subtle, ethereal vision of Mahatma Gandhi's Charkha (spinning wheel) blending into the shape of Lord Ganesha, blessing the land. Patriotic, serene, historical, deeply respectful."),

    ("sarga_10_02_shankaracharya_padukas.png",
     "The sacred wooden Padukas (sandals) of Adi Shankaracharya resting on a divine pedestal, radiating the pure, white light of Advaita (non-duality). A peaceful, highly meditative setting that embodies the eternal truth of Asti (Existence). Minimalist, spiritual, glowing aura."),
]

for filename, prompt in prompts:
    out_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(out_path):
        print(f"  skip (exists): {filename}")
        continue
    print(f"Generating: {filename} ...", end=" ", flush=True)
    try:
        response = client.images.generate(
            model="gpt-image-2",
            prompt=prompt,
            size="1024x1536",
            quality="high",
            n=1,
        )
        img_data = base64.b64decode(response.data[0].b64_json)
        with open(out_path, "wb") as f:
            f.write(img_data)
        print(f"saved ({len(img_data)//1024} KB)")
    except Exception as e:
        print(f"ERROR: {e}")
    time.sleep(2)  # DALL-E 3 rate limit: ~5 img/min on tier 1

print("\nDone.")
