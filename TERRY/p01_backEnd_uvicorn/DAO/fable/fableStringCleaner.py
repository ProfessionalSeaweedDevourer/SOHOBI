class fableStringCleaner:
    @staticmethod
    def clean(txt):
        for t in ["<b>", "</b>", "&gt;", "&lt;", "&quot;"]:
            txt = txt.replace(t, " ")
        return txt
    
