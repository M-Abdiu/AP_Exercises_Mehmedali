class Student(): 
    
    def __init__(self, id: int, lname: str, fname: str):
        self._id = id           #_id → Private, nicht sichtbar ausserhalb der Klasse. 
        self._lname = lname     # → encapsulation
        self._fname = fname


    #Getter-Methode: Property (Abrufen)
    @property
    def id(self):
        if not self._id:
            raise ValueError("ID is not defined.")
        return self._id[0]
    
    #Setter-Methode: Property (Setzen)
    @id.setter
    def id(self, value: int):
        self._id = value


    def __str__(self):  #Wie wird der String beim printen dargestellt
        return f"ID: {self._id}, Last Name: {self._lname}, First Name: {self._fname}"
    

    def __eq__(self, other):  #Wie sollend die Objekte verglichen werden
        if isinstance(other, Student):
            return self._id == other._id
        return False
    
    def __lt__(self, other):
        return self._id < other._id



s1 = Student(1, "Miller", "Mia")
s2 = Student(2, "Smith", "John")

list = [s1, s2]

print(s1._id)
print(s1)

print(s1 == s2)  #Vergleich der Objekte
print(s1 < s2)   #Vergleich der Objekte
for s in list:
    print(s)

