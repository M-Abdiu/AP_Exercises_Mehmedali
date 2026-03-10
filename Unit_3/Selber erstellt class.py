class Student(): 
    #Attribute
    _fname = ""
    _lname = ""

    #Methoden
    def ensure_capitalization(self):
        self._fname = self._fname.upper()
        self._lname = self._lname.upper()
        

    #Getter und Setter 
    @property
    def fname(self):
        return self._fname

    @_fname.setter
    def fname(self, value: str):
        self._fname = value



#um dann ein Objekt zu erstellen kann man z.B: 

s1 = Student()
s1._fname = "Mia"
s1._lname = "Miller"
s1.ensure_capitalization()

print(s1)