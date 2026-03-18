# PDF Service - INTEGRATED

⚠️ **IMPORTANT**: This PDF service has been **integrated into the main Next.js project**!

## New Location
The PDF generation functionality is now available at:
**`http://localhost:3001/api/pdf/generate`**

## Migration Complete ✅

### What Changed:
- ✅ PDF generation moved from separate FastAPI service to Next.js API route
- ✅ Uses `pdf-lib` instead of `reportlab` (already in your dependencies)
- ✅ Same API schema and functionality
- ✅ Better integration with your main application
- ✅ No need to run separate Python service

### How to Use:

1. **Start your main Next.js server:**
   ```bash
   cd adaptive-ai-health-onefolder
   npm run dev
   ```
   Server runs on `http://localhost:3001`

2. **Test PDF generation:**
   ```bash
   curl -X POST "http://localhost:3001/api/pdf/generate" \
     -H "Content-Type: application/json" \
     -d '{"patient_name":"Ashok","age":22,"symptoms":["Fever","Cough"],"prediction":"Cold"}' \
     --output report.pdf
   ```

3. **Use the HTML demo:**
   - Open `pdfService/index.html` in browser
   - It now connects to the integrated Next.js endpoint

## API Schema (Unchanged)
```json
{
  "patient_name": "string",
  "age": "number",
  "symptoms": ["string"],
  "prediction": "string"
}
```

## Benefits of Integration:
- 🎯 **Single codebase** - No separate services to manage
- 🔄 **Unified deployment** - Everything runs together
- 📦 **Fewer dependencies** - Uses existing Next.js stack
- 🚀 **Better performance** - Native Node.js execution
- 🛠️ **Easier debugging** - All logs in one place

---

**The separate PDF service is now deprecated. Use the integrated Next.js endpoint instead!** 🎉