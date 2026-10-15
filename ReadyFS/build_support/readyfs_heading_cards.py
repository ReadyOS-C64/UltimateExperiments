"""Viewer-facing ReadyFS cards; production details belong in evidence reports."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SD_ACTIONS = [
    ('Detect device 10', 'Probe the attached SD2IEC over native IEC.'),
    ('Inspect configuration', 'Read SD2IEC settings without changing them.'),
    ('Inspect partition 1', 'Check whether partition 1 shows folders or an image.'),
    ('Create an SD folder', 'Make a destination folder on the SD card.'),
    ('Name the SD folder', 'Use CARD as a short name for this folder.'),
    ('Inspect the source tree', 'Inspect the five files and their nested folders.'),
    ('Prepare the destination', 'Create TREE on the SD card for the copy.'),
    ('Preview a recursive copy', 'List selected files and folders without writing.'),
    ('Copy the folder tree', 'Copy nested folders to SD2IEC with verification.'),
    ('Inspect the SD copy', 'Confirm the SD copy retains every nested folder.'),
    ('Prepare the return folder', 'Create a host folder for the return copy.'),
    ('Copy back to the host', 'Read all five files back from SD2IEC.'),
    ('Inspect the returned tree', 'Check the returned files and folder structure.'),
    ('Prepare SoftwareIEC', 'Prepare a separate SoftwareIEC destination for SD files.'),
    ('Transfer to an IEC disk', 'Copy one SD file into the flat IEC image.'),
    ('Transfer to SoftwareIEC', 'Copy the same SD file through SoftwareIEC.'),
    ('Copy another IEC file', 'Copy a second SD file to the IEC disk.'),
    ('Copy another SoftwareIEC file', 'Copy the second SD file through SoftwareIEC.'),
    ('Mount a D64 image', 'Switch partition 1 from SD folders to image contents.'),
    ('Check the mounted partition', 'Confirm partition 1 now exposes the D64 image.'),
    ('Browse the D64 image', 'List files inside the mounted SD2IEC image.'),
    ('Copy into the SD image', 'Copy a returned host file into the mounted D64.'),
    ('SD image to Ultimate image', 'Copy from SD2IEC into a separate Ultimate D64.'),
    ('Copy a second image file', 'Copy a second host file into the SD image.'),
    ('Transfer the second file', 'Write the second file into the Ultimate D64.'),
    ('Ultimate image to SD image', 'Transfer a PRG back into the mounted SD image.'),
    ('Check the PRG file type', 'Confirm the SD image records the file as PRG.'),
    ('Stage the PRG on the host', 'Save the PRG before leaving the mounted image.'),
    ('Return to SD folders', 'Dismount the image to restore SD folder access.'),
    ('Copy the PRG onto SD', 'Copy the staged program into the SD folder.'),
    ('Compare the PRG contents', 'Compare the SD file with the original image file.'),
    ('Confirm configuration', 'Check SD2IEC settings after the transfers.'),
]

BATCH_ACTIONS = [
    ('Start the backup counter', 'Count successful backups with a shared session variable.'),
    ('Read the backup script', 'Inspect arguments, conditions and the copy subroutine.'),
    ('Preview the backup', 'Pass PREVIEW to see the plan without writing.'),
    ('Copy and verify', 'Pass APPLY to copy, compare and count the backup.'),
    ('Protect an existing file', 'Refuse an existing destination and keep its contents.'),
    ('Read the saved file', 'Inspect the text copied by the backup script.'),
    ('Show the backup count', 'Display the counter retained after the script finishes.'),
]

def make_card(title, description, *, band=False):
    fonts = Path('/System/Library/Fonts/Supplemental')
    heading = ImageFont.truetype(str(fonts/'Arial Bold.ttf'), 28)
    body = ImageFont.truetype(str(fonts/'Arial.ttf'), 21)
    assert len(description.split()) <= 10, description
    assert heading.getlength(title) < 775, title
    assert body.getlength(description) < 775, description
    card = Image.new('RGBA', (856, 104), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, 855, 103), radius=16,
                        fill=(23, 32, 51, 242), outline=(83, 105, 137, 242))
    d.rounded_rectangle((20, 20, 24, 83), radius=2, fill=(136, 213, 221, 255))
    d.text((42, 15), title, font=heading, fill=(243, 247, 255, 255))
    d.text((42, 58), description, font=body, fill=(211, 222, 241, 255))
    if not band:
        return card
    image = Image.new('RGB', (960, 144), (9, 14, 27))
    image.paste(card, (52, 12), card)
    return image

def sd_card(index, *, band=False):
    title, description = SD_ACTIONS[index]
    return make_card('SD2IEC / ' + title, description, band=band)

def batch_card(index, *, band=False):
    title, description = BATCH_ACTIONS[index]
    return make_card('Batch / ' + title, description, band=band)
