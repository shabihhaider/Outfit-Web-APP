# Exact Steps to Submit & Download Your Research Paper via Overleaf

---

## PART 1: CREATE OVERLEAF PROJECT & UPLOAD FILES

### Step 1: Open Overleaf
1. Go to: **https://www.overleaf.com**
2. Sign in to your Overaf account (or create one if needed)
3. Click **"New Project"** button (top-left)

### Step 2: Create New Blank Project
1. Select **"Blank Project"**
2. Name it: `Outfit-Recommendation-FYP-2026`
3. Click **"Create"**

### Step 3: Upload LaTeX Files
You now have an empty Overleaf project. Upload your files:

**Option A: Upload via Drag & Drop (Easiest)**
1. In the Overleaf file browser (left panel), locate the area showing file names
2. Open **File Explorer** on your computer
3. Navigate to: `D:\FYP\docs\`
4. Select both files:
   - `outfit_recommendation_apa7.tex`
   - `references.bib`
5. Drag both files into the Overleaf left panel
6. Wait for upload to complete (you'll see them appear in file list)

**Option B: Upload via Menu**
1. Click **"Upload"** button (with arrow icon) in Overleaf
2. Choose **"Select from your computer"**
3. Select `outfit_recommendation_apa7.tex` → Open
4. Repeat: Click **"Upload"** again
5. Select `references.bib` → Open
6. Wait for both to complete

### Step 4: Set Compiler & Bibliography Tool
1. Click **"Menu"** (top-left, gear icon)
2. Find **"Compiler"** dropdown → Select **"pdfLaTeX"**
3. Find **"Bibliography tool"** → Select **"Biber"**
4. Close the menu

---

## PART 2: COMPILE & VIEW

### Step 5: Compile the PDF
1. Look for the **green "Recompile"** button (right side)
2. Click it
3. Wait 10-15 seconds for compilation to complete
4. The PDF preview will appear on the right side

### Step 6: Check for Errors
- ✅ **No errors?** Great! Skip to Step 7
- ❌ **Red error box?** Scroll down in error panel to see details
  - Most likely cause: Bibliography not recognized
  - **Solution**: Ensure `references.bib` was uploaded (check file list on left)
  - Click "Recompile" again

### Step 7: View Full PDF
1. On the right side, you should see your compiled PDF
2. Scroll through to verify:
   - Title page with all author names ✅
   - Abstract section ✅
   - All citations appear as [1], [2], etc. ✅
   - References section at end with full bibliography ✅
3. Use **"Full Screen"** button (top-right of PDF) for better viewing

---

## PART 3: DOWNLOAD THE PDF

### Step 8: Download to Your Computer
1. Look for the **download icon** at the top of the PDF panel
2. Click the **down arrow** icon (should say "Download PDF" on hover)
3. File will download as: `outfit_recommendation_apa7.pdf`
4. Default location: Your Downloads folder

### Alternative Download Method:
1. Click **"Menu"** (gear icon, top-left)
2. Scroll down to **"Source"** section
3. Click **"Download as ZIP"** (downloads whole project)
4. Unzip the folder on your computer
5. Look for: `outfit_recommendation_apa7.pdf` (the compiled output)

---

## PART 4: VERIFY DOWNLOAD & PREPARE FOR SUBMISSION

### Step 9: Verify Downloaded PDF
1. Open the downloaded PDF in your PDF reader
2. Check:
   - [ ] Title page correct (all 4 authors listed)
   - [ ] Abstract section present
   - [ ] All sections readable
   - [ ] References section complete
   - [ ] No compilation errors visible
   - [ ] Total pages: 5-6 pages

### Step 10: Prepare for Submission to UET Lahore
1. **Rename the file** (optional but recommended):
   ```
   OutfitRecommendation_FYP_2026_FINAL.pdf
   ```

2. **Create submission folder**:
   ```
   D:\FYP\SUBMISSION_FINAL_2026\
   ```

3. **Copy to submission folder**:
   - PDF file
   - Original .tex file (as backup)
   - Original .bib file (as backup)
   - REVIEW_AND_FIXES.md (shows what was fixed)

4. **Verify file size**: Should be ~500KB - 2MB (reasonable for academic paper)

---

## TROUBLESHOOTING

### Issue: "Bibliography not showing in PDF"
**Solution:**
1. Click "Recompile"
2. Wait 30 seconds (biber needs time)
3. Try again

### Issue: "Citation numbers [?] instead of [1], [2]"
**Solution:**
1. Ensure `references.bib` is in same folder
2. Click "Recompile" 2-3 times
3. Bibliography appears on 3rd compile usually

### Issue: "PDF won't compile - red X"
**Solutions:**
1. Check that both files uploaded correctly:
   - Left panel should show: `outfit_recommendation_apa7.tex` AND `references.bib`
2. Click "Recompile" button again
3. If still fails, check error message - usually shows line number
4. Common issue: Missing `\end{document}` - already included, so shouldn't happen

### Issue: "Can't download PDF"
**Solution:**
1. Try refreshing page (Ctrl+R)
2. Wait 30 seconds after compile finishes
3. Try "Download as ZIP" instead
4. Extract ZIP and find PDF inside

---

## FINAL CHECKLIST BEFORE SUBMITTING TO UET

- [ ] PDF compiles without errors ✅
- [ ] All author names visible on title page ✅
- [ ] Abstract section complete ✅
- [ ] All citations visible in References (10 total) ✅
- [ ] Page count correct (~5-6 pages) ✅
- [ ] No red compilation errors ✅
- [ ] PDF downloaded to computer ✅
- [ ] File readable in PDF viewer ✅
- [ ] All sections readable and properly formatted ✅

---

## FILE LOCATIONS FOR REFERENCE

**Your Research Paper Files:**
```
D:\FYP\docs\
├── outfit_recommendation_apa7.tex      (Main paper - UPLOAD THIS)
├── references.bib                       (Bibliography - UPLOAD THIS)
├── RESEARCH_PAPER_BUILD.md             (Build instructions)
├── REVIEW_AND_FIXES.md                 (What was fixed - YOU JUST MADE THIS)
└── OVERLEAF_SUBMISSION_GUIDE.md        (This file - YOU JUST MADE THIS)
```

**After Download:**
```
D:\Downloads\
└── outfit_recommendation_apa7.pdf      (Your compiled paper - SUBMIT THIS)
```

---

## SUBMISSION DEADLINE

**Important**: Check with Ms. Darakhshan Bokhat for exact submission date/time

**Recommended**: Submit 24 hours early to avoid last-minute issues

---

## CONTACT & SUPPORT

If you encounter issues with Overleaf:
- **Overleaf Help**: https://www.overleaf.com/help
- **Documentation**: https://www.overleaf.com/learn

If you need to modify the paper:
1. Make changes in Overleaf editor (left side)
2. Changes compile automatically
3. Download new version when ready

---

**Good luck with your submission! Your research paper is ready. 🎓**
