"""
@name: Sceptic Bot
@author: Jiri Holba
@license: GNU Public License (GPL) version 3.0
@about: THE RESISTANCE Competition, Vienna Game/AI Conference 2012.
"""

from player import Bot 
from game import State
import random
import math
import itertools


class GameCombinations:
	def __init__(self, playerCnt, spyCnt):
		#self.combinations = []
		#cnt = math.factorial(playerCnt)/(math.factorial(spyCnt)*math.factorial(playerCnt - spyCnt))
		#indices = [i for i in range(spyCnt)]
		#for i in range(cnt):
		#	self.combinations.append([True if x in indices else False for x in range(playerCnt)])
		#
		#	for j in range(spyCnt-1, -1, -1):
		#		if indices[j] < (playerCnt - spyCnt + j):
		#			indices[j] += 1
		#			for k in range(j+1, spyCnt):
		#				indices[k] = indices[k-1]+1
		#			break
		# next line do the same. Should work for any number of players and spies
		self.combinations = map(lambda x: [True if y in x else False for y in range(playerCnt)], itertools.combinations(range(playerCnt),spyCnt))
	
	def addSabotage(self, team, sabotage):
		# remove those combinations which are not possible for given combination of team and number of sabotages
		reducedCombinations = []
		for c in self.combinations:
			if self._countOfSpies(team, c) >= sabotage:
				reducedCombinations.append(c)
		self.combinations = reducedCombinations
		
	def _countOfSpies(self, team, row):
		r = 0
		for p in team:
			if row[p.index] == True:
				r += 1
		return r
				
	def getProbabilities(self):
		# returns list of probabilities for player calculated from rest team combinations
		cnt = len(self.combinations)
		res = [0 for i in range(len(self.combinations[0]))] 
		for c in self.combinations:
			for j in range(len(c)):
				if c[j]:
					res[j] += 1
		return map(lambda x: float(x)/cnt, res)
		
class SampledValue:
	# class which calculates mean value from given samples
	def __init__(self, initValue):
		self.sampleCnt = 1
		self.sampleSum = initValue
	
	def add(self, value):
		self.sampleSum += value
		self.sampleCnt += 1
		
	def get(self):
		return 0 if (self.sampleCnt == 0) else (float(self.sampleSum) / float(self.sampleCnt))  
		
	def __repr__(self):
		return "Sample cnt: %0.1f sample sum: %0.1f" % (self.sampleCnt, self.sampleSum)
		
class SampledValueNonLinear:
	# calculated mean value from samples but gives more weight to values closer to extremes
	# so for values 0.5 and 0.9 returns 0.85 instead of 0.7
	def __init__(self, initValue):
		self.sampleCnt = 1
		self.sampleSum = initValue
	
	def add(self, value):
		weight = math.fabs(0.5-value)*50.0
		self.sampleSum += value * weight
		self.sampleCnt += weight
		
	def get(self):
		return 0 if (self.sampleCnt == 0) else (float(self.sampleSum) / float(self.sampleCnt))  
		
	def __repr__(self):
		return "Sample cnt: %0.1f sample sum: %0.1f" % (self.sampleCnt, self.sampleSum)
	
class PlayerInfo:
	# this class holds suspicions from player actions 
	def __init__(self, player):
		self.suspicionFromActions = SampledValueNonLinear(0.5)
		self.suspicion = 0.5
		self.player = player
		self.selectedPlayers = []
	
	def onSuspiciousAction(self, spyProb):
		self.suspicionFromActions.add(float(spyProb))
		
	def onTrustedAction(self, resProb):
		self.suspicionFromActions.add(float(1) - float(resProb))
		
	def onTeamSelected(self, team):
		self.selectedPlayers.append(team)
		
	def isSpy(self):
		return self.suspicion > 0.99
	
	def updateSuspicion(self, spyRatio):
		if spyRatio < 0.1 or spyRatio > 0.9:
			self.suspicion = spyRatio
		else:
			self.suspicion = (spyRatio + self.suspicionFromActions.get()*2.0)/3.0
	
	def __repr__(self):
		return "<%i-%s %0.2f %0.2f>" % (self.player.index, self.player.name, self.suspicionFromActions.get(), self.suspicion)
		
		
class PlayerStatistics:
	def __init__(self):
		# probability of player sabotage mission when is on it
		self.sabotage = SampledValue(0.8)
		# probability that player votes against the team in first turn
		self.spyVotesFalseFirstTurn = SampledValue(0.5)
		self.resVotesFalseFirstTurn = SampledValue(0.5)
		# probability that player votes for team with spy in it
		self.spyVotesForSpy = SampledValue(0.5)
		self.resVotesForSpy = SampledValue(0.5)
		# when spy selects players for mission, how often he selects another spy to team
		self.spySelectsOtherSpy = SampledValue(0.5)
		# in game of 5 players, what is probability that player who is not in team votes for team
		self.spyVotesForFullTeam = SampledValue(0.5)
		self.resVotesForFullTeam = SampledValue(0.5)

class ScepticBot(Bot):
	"""Don't trust anyone."""

	playerStats = {}

	def onGameRevealed(self, players, spies):
		self.playerInfos = [PlayerInfo(p) for p in players if p.index != self.index]
		self.spies = spies
		
		spyCntDict = {5:2, 6:2, 7:3, 8:3, 9:3, 10:4}
		self.playersCnt = len(players)
		self.spiesCnt = spyCntDict[self.playersCnt]
		
		self.gameCombinations = GameCombinations(self.playersCnt, self.spiesCnt)
		if not self.spy:
			others = [p for p in players if p.index != self.index]
			# remove all combinations containing me as a spy from combinations
			self.gameCombinations.addSabotage(others, self.spiesCnt)
		
		for p in players:
			self.playerStats.setdefault(p.name, PlayerStatistics())

		# members to store info about game flow
		self.missions = []
		self.votes = []
		self.selections = []
		
	def select(self, players, count):
		#if self.game.turn == 1:
		#	# in first turn, select other players to try force spies to reveal themselves
		#	others = [p.player for p in self.playerInfos if p.player != self]
		#	others.sort(key=lambda x: self._getSpyRatio(x, 'spyVotesFalseFirstTurn', 'resVotesFalseFirstTurn'))
		#	return others[:count]
		# this idea didn't work at all
		
		# playerInfos are sorted by suspicion value, select less suspicious players + me
		others = [p.player for p in self.playerInfos if p.player not in self.spies]
		me = [p for p in players if p.index == self.index]
		if self.spy:
			# spy selects most suspicious resistance players
			return me + others[len(others)-(count-1):]
		else:
			# resistance selects less suspicious players
			return me + others[:count -1]

	def onTeamSelected(self, leader, team):
		# store for statistics
		self.selections.append((self.game.leader, team)) 
		
		if leader == self:
			return
			
		leaderInfo = [p for p in self.playerInfos if p.player == leader][0]
		# store selected team for future. When we reveal spy we can process this data
		leaderInfo.onTeamSelected(team)
		
		if leaderInfo.isSpy():
			self._processSpySelections(leaderInfo)
			
	def vote(self, team): 
		
		if self.game.turn == 1: # always vote True in first turn
			return True

		# resistance has no reason to vote false, so don't reveal myself and vote always true
		if self.game.tries == 5:
			return True
		
		# num players in team equal to num of resistance and I'm not there -> one of them is spy	
		if len(self.game.team) == (self.playersCnt - self.spiesCnt) and not self in self.game.team:
			return False

		if self.spy:
			if len(self.game.team) == len([p for p in self.game.team if p in self.spies]):
				return False
		
			res = len([p for p in self.game.team if p in self.spies]) > 0
			return res

		suspicionLimit = self.playerInfos[self.playersCnt-self.spiesCnt-1].suspicion
		if set(team).intersection([p.player for p in self.playerInfos if p.suspicion >= suspicionLimit]):
			return False

		return True
		

	def onVoteComplete(self, votes):
		
		self.votes.append((self.game.turn, self.game.team[:], votes))
		self.lastVotes = votes
		
		# when all players are against the team, there is probably no spy in it
		# the probability is the lowest probability that spy votes for spy
		if not reduce(lambda x, y: x if x else y, votes, False):
			s = reduce(lambda x,y: self.playerStats[y.name].spyVotesForSpy.get() if self.playerStats[y.name].spyVotesForSpy .get() < x else x, self.game.team, 1.0)
			if s > 0.5: # only when spies votes for spies in more than half votings
				for pi in [pi for pi in self.playerInfos if pi.player in self.game.team]:
					pi.onTrustedAction(s)
		
		# suspect players who vote against team in first turn
		if self.game.turn == 1:
			for pi in [pi for pi in self.playerInfos if not votes[pi.player.index]]:
				ratio = self._getSpyRatio(pi.player, 'spyVotesFalseFirstTurn', 'resVotesFalseFirstTurn')
				pi.onSuspiciousAction(ratio)
		else:
			# reduce suspicion for player who woted against the team when I'm against the team
			if not self.spy and not votes[self.index]:
				for pi in [pi for pi in self.playerInfos if not votes[pi.player.index]]:
					pi.onTrustedAction(0.8) # TODO remove this hardcoded value
					
			# when it's team with lenght equal to number of resistance, those who are not in it and vote for team may be spies
			if len(self.game.team) == (self.playersCnt - self.spiesCnt):
				for pi in [pi for pi in self.playerInfos if votes[pi.player.index] and pi.player not in self.game.team]:
					ratio = self._getSpyRatio(pi.player, 'spyVotesForFullTeam', 'resVotesForFullTeam')
					pi.onSuspiciousAction(ratio)
					
		if self.game.tries == 5:
			# suspect players who wote against the team in last try
			for pi in [pi for pi in self.playerInfos if not votes[pi.player.index]]:
				pi.onSuspiciousAction(1.0) # TODO maybe should not be hardcoded
			
		self._updatePlayersSuspicions()
		
	
	def sabotage(self):
		if self.game.losses == 2 or self.game.wins == 2:
			return True

		#if self.game.turn == 1 or len(self.game.team) == 2:
		#	return False
	
		spiesOnMission = [s for s in self.spies if s in self.game.team]
		if len(spiesOnMission) == len(self.game.team):
			return False
	
		if len(spiesOnMission) > 1:
			p = sum([self.playerStats[s.name].sabotage.get() for s in spiesOnMission if s != self])/float(len(spiesOnMission)) 
			# randomly sabotage based on probability that other spy will sabotage. But we are sceptic, so lower the value little bit
			return random.random() >= (p*p)
		
		return True
		
	def onMissionComplete(self, sabotaged):
		
		self.missions.append((self.game.team[:], sabotaged))
		
		# trust players who didn't sabotage mission
		if sabotaged == 0:
			# dont trust too much to team that was approved by all players
			for pi in [pi for pi in self.playerInfos if pi.player in self.game.team]:
				if reduce(lambda x, y: x if not x else y, self.lastVotes, True):
					susp = (self.playerStats[pi.player.name].sabotage.get()+0.5)/float(2)
				else:
					susp = self.playerStats[pi.player.name].sabotage.get()
				pi.onTrustedAction(susp)
				
			# num players in team equal to num of resistance and mission passed. I'm almost sure that players not in mission are spies	
			if not self.spy and len(self.game.team) == (self.playersCnt - self.spiesCnt) and self in self.game.team:
				# probability that player which are not on missions are spies is equal to lowest probability of sabotage from team players
				susp = reduce(lambda x,y: self.playerStats[y.name].sabotage.get() if self.playerStats[y.name].sabotage.get() < x else x, self.game.team, 1.0)
				for pi in [pi for pi in self.playerInfos if pi.player not in self.game.team]:
					pi.onSuspiciousAction(susp)
					
				
		else:
			self.gameCombinations.addSabotage(self.game.team, sabotaged)
			
			# don't trust to players who woted for spies. Except first turn
			if self.game.turn != 1:
				for pi in [ pi for pi in self.playerInfos if self.lastVotes[pi.player.index]]:
					pi.onSuspiciousAction(self._getSpyRatio(pi.player, 'spyVotesForSpy', 'resVotesForSpy'))
							
			
		self._updatePlayersSuspicions()
		
	def onGameComplete(self, win, spies):
		# process all stored data to update statistics
		for team, sabotaged in self.missions:
			spiesOnMission = [p for p in team if p in spies]
			if len(spiesOnMission) > 0:
				for spy in spiesOnMission:
					self.playerStats[spy.name].sabotage.add(float(sabotaged) / float(len(spiesOnMission)))
					
		for turn, team, votes in self.votes:
			if turn == 1:
				for p in team:
					if p in spies:
						self.playerStats[p.name].spyVotesFalseFirstTurn.add(0 if votes[p.index] else 1)
					else:
						self.playerStats[p.name].resVotesFalseFirstTurn.add(0 if votes[p.index] else 1)
			else:
				if set(team).intersection(spies):
					for p in self.game.players:
						if p in spies:
							self.playerStats[p.name].spyVotesForSpy.add(1 if votes[p.index] else 0)
						else:
							self.playerStats[p.name].resVotesForSpy.add(1 if votes[p.index] else 0)
							
				if len(team) == (self.playersCnt - self.spiesCnt):
					for p in [p for p in self.game.players if p not in team]:
						if p in spies:
							self.playerStats[p.name].spyVotesForFullTeam.add(1 if votes[p.index] else 0)
						else:
							self.playerStats[p.name].resVotesForFullTeam.add(1 if votes[p.index] else 0)
	
		for leader, team in self.selections:
			isSpyInTeam = len([p for p in team if p in spies and p != leader]) > 0
			if leader in spies:
				self.playerStats[p.name].spySelectsOtherSpy.add(1 if isSpyInTeam else 0)
	

	def _updatePlayersSuspicions(self):
		spyRatios = self.gameCombinations.getProbabilities()	
		for p in self.playerInfos:
			spyRatio = spyRatios[p.player.index]
			if spyRatio > 0.99:
				self._processSpySelections(p)
			p.updateSuspicion(spyRatio)
				
		self.playerInfos.sort(key=lambda x: x.suspicion)	

	def _getSpyRatio(self, player, spyAttr, resAttr):
		s = self.playerStats[player.name].__dict__[spyAttr].get()
		r = self.playerStats[player.name].__dict__[resAttr].get()
		return 0 if (s+r) == 0 else (s / (s + r))
		
	def _processSpySelections(self, leaderInfo):
		if len(leaderInfo.selectedPlayers) == 0: 
			return
			
		ratio = self.playerStats[leaderInfo.player.name].spySelectsOtherSpy.get()
		for p in self.playerInfos:
			if p in leaderInfo.selectedPlayers:
				p.onSuspiciousAction(ratio)
			else:
				p.onTrustedAction(ratio)
	
		leaderInfo.selectedPlayers = []
