import openai
import requests
import random
import discord
import similarity
import math
import time
from enum import Enum
from PIL import Image
from io import BytesIO
from decouple import config


#ENUM to handle the state of the game
class State(Enum):
    PREPARING = 0
    GUESSING = 1
    CORRECT = 2
    STOP = 3


#Create class to manage game
class Game:

    def __init__(self) -> None:
        pass

    def initiate(self, game_channel_text, game_channel_voice, client):
        self.prompt = None
        self.scoreboard = {}
        self.prompted_player = None
        self.game_channel_text = game_channel_text
        self.game_channel_voice = game_channel_voice
        self.curr_players = self.game_channel_voice.members
        self.client = client    
        self.state = State.PREPARING
        self.wrong_guesses = 0
        self.hints = []
        self.hint_index = 0

        self.reset_game()


    def reset_score(self):
        for player in self.curr_players:
            self.scoreboard[player.name] = 0
    
    def reset_game(self):
        self.reset_score()

    #get the prompt from the user
    async def get_prompt(self):

        #choose a player to get the prompt from
        chosen_player = random.choice(self.curr_players)
        while(chosen_player == self.prompted_player):
            chosen_player = random.choice(self.curr_players)

        self.prompted_player = chosen_player

        #send message to everyone of who is choosing the prompt
        await self.game_channel_text.send(f"{chosen_player} is choosing a prompt for everyone to guess...")

        #profanity check
        valid = False

        while not valid:
            #get the prompt from user
            await chosen_player.send("Create a prompt for the players to guess")

            def check(m):
                return m.author == chosen_player
            
            message = await self.client.wait_for('message', check=check)
            self.prompt = message.content

            if similarity.profanity_check(self.prompt):
               valid = True
            else:
                await chosen_player.send("There was an error with your prompt: Profanity was detected, please enter again") 

        self.prompt.upper()



    def generate_image(self):

        #get key
        openai.api_key = config('OPEN_AI_KEY')

        try:
            response = openai.Image.create(
                prompt=self.prompt
            )

            image_url = response['data'][0]['url']

            response = requests.get(image_url)

            img = Image.open(BytesIO(response.content))

            img.save('generatedImage.png')
            return 0, None
        except openai.OpenAIError as e:
            return 1, e

    async def update_score(self, player):
        self.scoreboard[player.name] += 1

        #display score
        await self.display_score()
    
    async def display_score(self):
        #sort the scoreboard to get highest player first
        dict(sorted(self.scoreboard.items(), key=lambda item: item[-1]))

        await self.game_channel_text.send("Players\tScore")

        place = 1
        for player in self.scoreboard:
            await self.game_channel_text.send(f"{place}: {player}\t{self.scoreboard[player]}")
            place += 1

    async def get_hints(self):
        #prompt user
        def check(m):
            return m.author == self.prompted_player
        
        await self.prompted_player.send("You will need to create 3 hints to help the players.\nPlease send the first hint")
        num = 1

        while num <= 3:

            message = await self.client.wait_for('message', check=check)

            hint = message.content
            self.hints.append(hint)

            num += 1
            if num < 4:
                await self.prompted_player.send(f"Send hint {num}")
        
        print (self.hints)

    async def parse_commands(self, command):

        if command.startswith("$scoreboard"):
            await self.display_score()
        elif command.startswith('$skip'):
            self.state = State.PREPARING
            await self.game_channel_text.send("Skipping this turn, no one gets rewarded a point")
        elif command.startswith('$stop'):
            self.state = State.STOP
            await self.game_channel_text.send('Stopping the game...')
        else:
            await self.game_channel_text.send(f'{command} is not a recongnised command')


    #run game 
    async def run(self):

        while (self.state != State.STOP):

            if len(self.curr_players) < 2:
                await self.game_channel_text.send("There is not enough players to start a game:(")
                return False

            #get prompt and prepare users
            if (self.state == State.PREPARING):

                await self.get_prompt()

                result, error = self.generate_image()

                if result == 1:
                    await self.game_channel_text.send("Error occurred while processing the prompt game is ending :(")
                    print (error)
                    self.state = State.STOP 

                #create the hints
                await self.get_hints()

                #send the image to the chat
                await self.game_channel_text.send(file=discord.File("generatedImage.png"))

                await self.game_channel_text.send(f"Guess what {self.prompted_player} made me generate")

                self.state = State.GUESSING

            elif (self.state == State.GUESSING):

                #get guesses from users
                def check(m):
                    return m.author in self.curr_players

                message = await self.client.wait_for('message', check=check)

                guess = message.content

                if guess.startswith('$'):
                    await self.parse_commands(guess)

                elif message.author != self.client.user and message.author != self.prompted_player:

                    
                    guess.upper()

                    #Check similarity
                    sim = similarity.process(guess, self.prompt)
                    print(f"similarity:{sim}")

                    #Use thresholds to determine next step
                    if sim > 0.9: #CORRECT
                        #update the score

                        await self.game_channel_text.send(f"{message.author} is CORRECT!\nThe correct prompt was {self.prompt}")

                        self.state = State.CORRECT
                        await self.update_score(message.author)

                    elif sim > 0.75: #CLOSE GIVE HINTS
                        
                        keywords_guess = similarity.keywords(guess)
                        keywords_prompt = similarity.keywords(self.prompt)

                        intersection = []
                        check = 0

                        for word in keywords_guess:
                            #only allow maximum of 3 words 
                            if check > 3:
                                break
                            if word in keywords_prompt:
                                intersection.append(word)
                                check += 1

                        #join to a single string
                        intersection = ", ".join(intersection)

                        #send list of common words back to player who guess
                        await message.author.send(f"These are the words you got correct\n{intersection}")
                        await self.game_channel_text.send(f"{message.author} was close, we provided them with a hint!!")

                    else: #WRONG
                        self.wrong_guesses += 1

                        if self.wrong_guesses > 3:
                            self.game_channel_text.send(f"Too many wrong guesses here's a hint provided from {self.prompted_player}\n\"{self.hints[self.hint_index]}\"")
                            self.hint_index += 1
                        
                        if math.isnan(sim):
                            sim = 0

                        await self.game_channel_text.send(f"incorrect guess from {message.author}, you were {math.floor(sim * 100)}% correct")

            else: #Someone got it right
                #check if want to play again
                await self.game_channel_text.send("Want to go again?")

                def check(m):
                    return m.author != self.client.user
                message = await self.client.wait_for('message', check=check)
                
                response = message.content
                
                response.upper()

                if response.startswith("N"):
                    self.state = State.STOP
                    return True
                else:
                    self.state = State.PREPARING
            
        
        
        #thanks for playing
        await self.game_channel_text.send("Thank you for playing, here are the final standings")

        await self.display_score()
        
        return False

    def add_player(self, player):
        print(f"adding {player} to the list of players")
        if player not in self.curr_players:
            self.curr_players.append(player)

    def remove_player(self, player):
        print (f"removing {player} from list of players")
        if player in self.curr_players:
            self.curr_players.remove(player)

    

'''
TODO suggestions
- make roles to take away from switching back and forth 
    - between dms and server
'''