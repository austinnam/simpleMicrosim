from numpy.random import choice
import math
import numpy as np
import time

class Parameters:
    cycleLength = 1/12 # monthly cycle length, units = years
    discRate = 0.015

    mortCOPD = np.array([0.0060, math.log(1.3), math.log(2.0), math.log(4.5), math.log(11.6), math.log(0.9), math.log(1.4), math.log(2.6), math.log(1.5)])


class Calculator:
    @classmethod
    def probToRate(cls, p, t=1):
        return (-math.log(1-min(1,p))/t)

    @classmethod
    def rateToProb(cls, r, t=1):
        return (1-math.exp(-r*t))

    # conversion of yearly probability to cycle length probability
    @classmethod
    def probToCycleLength(cls, p, cl):
        return (cls.probToRate(cls.rateToProb(cls.probToRate(p)*cl)))

    @classmethod
    def getDiscount(cls,dr,tElapsed):
        return 1/((1+dr)**tElapsed)


class HealthState(Calculator, Parameters):
    totalCost = 0.0
    hsNames = np.array(["Current", "Former", "Dead"])

    def __init__(self):
        self.tpDie = 0.05
        self.tpFormer = 0.2
        self.tpCurrent = 1-0.05-0.2
        self.stateCost = 0.0

    def calcTransition(self,ag):
        return 0

    def getTransition(self, ag):
        self.calcTransition(ag)
        return choice(HealthState.hsNames, 1, p=[self.tpCurrent, self.tpFormer, self.tpDie])

    def getStateCost(self, ag):
        HealthState.totalCost += self.stateCost*HealthState.cycleLength*HealthState.getDiscount(HealthState.discRate, ag.yearsElapsed)

    def getProbDie(self, male, age, gold, smoker):
        return HealthState.mortCOPD[0] * math.exp(HealthState.mortCOPD[1]*male + HealthState.mortCOPD[2]*(age>=60 and age<70) + HealthState.mortCOPD[3]*(age>=70 and age<80) + HealthState.mortCOPD[4]*(age>=80) + HealthState.mortCOPD[5]*(gold==1) + HealthState.mortCOPD[6]*(gold==2) + HealthState.mortCOPD[7]*(gold>=3) + HealthState.mortCOPD[8]*smoker)

    def processEvents(self, ag):
        return 0


class CurrentSmoker(HealthState):
    def __init__(self):
        self.tpDie = 0.005
        self.tpFormer = 0.06
        self.tpCurrent = 1-self.tpFormer-self.tpDie

        self.stateCost = 2000

    def calcTransition(self, ag):
        self.tpDie = Calculator.probToCycleLength(HealthState.getProbDie(self, ag.male, ag.age, ag.gold, ag.smoker), HealthState.cycleLength)
        self.tpFormer = (1-self.tpDie) * Calculator.probToCycleLength(0.06, HealthState.cycleLength)
        self.tpCurrent = max(0, 1-self.tpFormer-self.tpDie)

    def processEvents(self, ag):
        ag.durationAbst = 0

class FormerSmoker(HealthState):
    def __init__(self):
        self.tpDie = 0.2
        self.tpCurrent = 0.94
        self.tpFormer = 1-self.tpDie-self.tpCurrent

        self.stateCost = 5000

    def calcTransition(self, ag):
        self.tpDie = Calculator.probToCycleLength(HealthState.getProbDie(self, ag.male, ag.age, ag.gold, ag.smoker), HealthState.cycleLength)

        # Probability of relapse dependent on duration of abstinence
        if ag.durationAbst < 5:
            self.tpCurrent = (1-self.tpDie) * (Calculator.probToCycleLength(0.42, HealthState.cycleLength))
        else:
            self.tpCurrent = 0

        self.tpFormer = max(0, 1-self.tpCurrent-self.tpDie)

    def processEvents(self, ag):
        ag.durationAbst += HealthState.cycleLength


class Dead(HealthState):
    def __init__(self):
        self.tpDie = 1
        self.tpFormer = 0
        self.tpCurrent = 0

        self.stateCost = 0


class Person(Parameters):
    personCount = 0

    def __init__(self, initHealthState):

        self.id = Person.personCount
        self.hs = initHealthState
        self.alive = 1
        self.yearsElapsed = 0

        self.age = 50
        self.male = 1
        self.gold = 2
        self.smoker = 1
        self.durationAbst = (1-self.smoker)*(0)

        Person.personCount += 1

startTime = time.time()

c = CurrentSmoker()
f = FormerSmoker()
d = Dead()

countQuit = 0
numPersons = 1000

for i in range(0,numPersons):
    ag = Person(c)

    while ag.alive==1:

        # update time
        ag.age += ag.cycleLength
        ag.yearsElapsed += ag.cycleLength

        ag.hs.processEvents(ag)

        t = ag.hs.getTransition(ag)

        if t=="Current":
            ag.hs = c
            ag.smoker = 1
        elif t=="Former":
            ag.hs = f
            ag.smoker = 0
        else:
            ag.hs = d
            ag.alive = 0

        ag.hs.getStateCost(ag)

    if ag.durationAbst >= 5:
        #print(ag.id)
        countQuit += 1

    del ag

endTime = time.time()
print("Proportion quit:", countQuit/numPersons, "Runtime:", endTime-startTime)

#print("Total cost: ", ag.hs.totalCost)
