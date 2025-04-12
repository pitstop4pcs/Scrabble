import os

import random
import socket
import subprocess
import threading

import psutil
import pygame

from constants import *
from sprites import *


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Scrabble by Pi")
        pygame.display.set_icon(pygame.image.load(resource_path("scrab.ico")).convert_alpha())
        self.running = True
        self.clock = pygame.time.Clock()
        self.screen.fill("green")
        self.across_arrow = pygame.image.load(resource_path("across.png")).convert_alpha()
        self.down_arrow = pygame.image.load(resource_path("down.png")).convert_alpha()
        self.current_arrow = self.across_arrow
        self.panel_font = pygame.font.Font(resource_path("fonts/InterstateBold.otf"), 36)
        self.small_font = pygame.font.SysFont(resource_path("fonts/InterstateBold.otf"), 34)
        self.scrabble_font = pygame.font.Font(resource_path("fonts/Scramble-KVBe.ttf"), TILE_SIZE)
        self.title = self.scrabble_font.render("Scrabble", True, "black")
        self.title_rect = self.title.get_rect(topleft=(TILE_SIZE * 17.7, TILE_SIZE // 2))

        self.host_join_buttons = {}

        self.tilerack = pygame.Surface((TILE_SIZE * 8, TILE_SIZE * 1.5))
        self.tilerack_rect = self.tilerack.get_rect(topleft=(TILE_SIZE * 18, TILE_SIZE * 13.5))
        self.tilerack.fill("lightgoldenrod")
        pygame.draw.rect(self.tilerack, "black", (0, 0, TILE_SIZE * 8, TILE_SIZE * 1.5), 1)
        self.tiles_on_rack = pygame.sprite.Group()
        self.tilerack_slots = pygame.sprite.Group()
        for i in range(7):
            TileRackSlot(self.tilerack_rect.x + TILE_SIZE // 8.33 + i * (TILE_SIZE + TILE_SIZE // 8.33),
                         TILE_SIZE // 4 + self.tilerack_rect.y).add(self.tilerack_slots)

        self.bag = pygame.Surface((TILE_SIZE * 10, TILE_SIZE * 6))
        self.bag_rect = self.bag.get_rect(topleft=(TILE_SIZE * 17, TILE_SIZE * 2))
        self.bag.fill("darkgreen")
        self.tiles_in_bag = pygame.sprite.Group()
        for tile in TILES.keys():
            for _ in range(TILES[tile][1]):
                Tile(-50, -50, tile, TILES[tile][0]).add(self.tiles_in_bag)

        self.tiles_being_swapped = pygame.sprite.Group()
        self.swap_area = pygame.Surface((TILE_SIZE * 8, TILE_SIZE * 4.5))
        self.swap_area_rect = self.swap_area.get_rect(topleft=(TILE_SIZE * 18, TILE_SIZE * 8.5))
        self.swap_area.fill("darkgreen")

        self.gameboard_squares = pygame.sprite.Group()
        self.tiles_on_board = pygame.sprite.Group()
        for row in range(15):
            for col in range(15):
                Square(TILE_SIZE + row * TILE_SIZE, TILE_SIZE // 2 + col * TILE_SIZE,
                       COLOURS[SQUARE_COLOUR[row][col]]).add(self.gameboard_squares)

        self.tile_in_hand = pygame.sprite.GroupSingle()
        self.tiles_played = pygame.sprite.Group()

        self.all_words = {}
        self.words_on_board = {}
        self.new_words = {}
        self.blank = False
        self.swap_area_tooltip = False

        self.potential_score = None
        self.score = 0
        self.opponents_score = 0

        self.host_ip = ""
        self.host = None
        self.client = None
        self.role = None

        self.establishing_connection = True
        self.distributing = False
        self.your_turn = False

        self.opponents_move = {"h": [], "c": []}
        self.gone_out = ""
        self.result = None

        self.pass_count = 0

    def run(self):
        while self.running:
            if self.gone_out == "t":
                self.your_turn = False
            if self.distributing:
                if self.your_turn:
                    self.draw_new_tiles()
                    self.send_move()
                    self.distributing = False
                    self.your_turn = False
                else:
                    if self.opponents_move["h" if self.role == "client" else "c"]:
                        self.distributing = False
                        self.update_data()
                        self.opponents_move["h" if self.role == "client" else "c"].clear()
                        self.draw_new_tiles()
                        self.send_move()
                        self.your_turn = False

            if not self.your_turn:
                if self.opponents_move["h" if self.role == "client" else "c"]:
                    self.remove_tiles_from_swap_area()
                    self.remove_tiles_from_board()
                    self.remove_arrow()
                    self.potential_score = None
                    self.update_data()
                    self.your_turn = True

            for event in pygame.event.get():
                if not self.blank:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        self.mouse_click(event.pos)
                    if event.type == pygame.MOUSEBUTTONUP:
                        if self.tile_in_hand:
                            self.mouse_release(event.pos)
                if event.type == pygame.QUIT:
                    self.running = False

                if event.type == pygame.KEYDOWN:
                    self.key_press(event.key)

                self.mouse_over(pygame.mouse.get_pos())

            if self.tiles_being_swapped:
                for i, tile in enumerate(self.tiles_being_swapped):
                    tile.update((self.swap_area_rect.x + TILE_SIZE // 3 * 2 + i * (TILE_SIZE + TILE_SIZE // 8.33),
                                 self.swap_area_rect.bottom - TILE_SIZE))

            if self.tile_in_hand:
                self.tile_in_hand.update(pygame.mouse.get_pos())

            self.display_update()
            self.clock.tick(FPS)

        pygame.quit()
        psutil.Process(os.getpid()).terminate()

    def mouse_over(self, pos):
        if self.swap_area_rect.collidepoint(pos):
            self.swap_area_tooltip = True
        else:
            self.swap_area_tooltip = False
        if self.tile_in_hand:
            for tile in self.tiles_on_rack:
                if tile.rect.collidepoint(pos):
                    slots = TILERACK_SLOTS.copy()
                    slots.remove(tile.rect.topleft)
                    rack_tiles = sorted(self.tiles_on_rack, key=lambda e: e.rect.x)
                    for i, t in enumerate(rack_tiles):
                        t.rect.topleft = slots[i]
                    return

    def key_press(self, key):
        if self.establishing_connection:
            if self.role == "client":
                if pygame.key.name(key).strip("[]").isnumeric() or pygame.key.name(key).strip("[]") == ".":
                    self.host_ip += pygame.key.name(key).strip("[]")
                    self.display_update()
                if key == pygame.K_ESCAPE or key == pygame.K_BACKSPACE:
                    self.host_ip = ""
                if key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
                    self.connect_to_host()

        if key == pygame.K_ESCAPE:
            self.potential_score = None
            self.remove_arrow()
            self.remove_tiles_from_board()
            self.remove_tiles_from_swap_area()
            self.blank = False

        if key == pygame.K_BACKSPACE:
            self.remove_arrow()
            if self.tiles_played:
                self.delete_last_letter_played()
                self.blank = False

        if self.blank:
            if 97 <= key <= 122:
                self.tiles_played.sprites()[-1].update(letter=chr(key))
                self.blank = False
                self.move_arrow()
                self.calculate_score()
        else:
            if 97 <= key <= 122:
                for tile in self.tiles_on_rack:
                    if tile.letter == chr(key):
                        for square in self.gameboard_squares:
                            if square.selected:
                                tile.update(square.rect.center)
                                tile.add(self.tiles_played)
                                tile.remove(self.tiles_on_rack)
                                self.move_arrow()
                                self.calculate_score()
                                return
                try:
                    for tile in self.tiles_on_rack:
                        if tile.score == 0:
                            old_key = key
                            self.key_press(32)
                            self.key_press(old_key)
                            return
                except RecursionError as err:
                    print(err)

            if key == 32:
                for tile in self.tiles_on_rack:
                    if tile.letter == "!":
                        for square in self.gameboard_squares:
                            if square.selected:
                                tile.update(square.rect.center)
                                tile.add(self.tiles_played)
                                tile.remove(self.tiles_on_rack)
                                self.calculate_score()
                                self.blank = True
                                return

            if self.your_turn:
                if key == pygame.K_RETURN:
                    self.remove_arrow()
                    if not self.check_legitimate():
                        self.key_press(pygame.K_ESCAPE)
                        return
                    if self.potential_score:
                        self.score += self.potential_score[0]
                    self.potential_score = None
                    for tile in self.tiles_played:
                        tile.add(self.tiles_on_board)
                        tile.remove(self.tiles_played)
                    self.get_words_on_board()
                    self.draw_new_tiles()
                    if not self.tiles_on_rack:
                        self.gone_out = "y"
                    self.send_move()
                    self.your_turn = False

    def update_data(self):
        bag, score, tob, gone_out, pc = self.opponents_move["h" if self.role == "client" else "c"][0].strip("'").split(
            "|")
        self.opponents_move["h" if self.role == "client" else "c"].clear()
        self.create_tiles_in_bag_from_list(bag)
        if self.gone_out == "y":
            if int(score) < self.opponents_score:
                self.score += self.opponents_score - int(score)
        self.opponents_score = int(score)
        if tob:
            self.create_tiles_on_board_from_list(tob)
        if gone_out == "y":
            for tile in self.tiles_on_rack:
                self.score -= tile.score
                self.opponents_score += tile.score
            self.gone_out = "t"
            self.send_move()
            self.end_game()
        if gone_out == "t":
            if self.gone_out == "t" or self.gone_out == "y":
                self.end_game()
            for tile in self.tiles_on_rack:
                self.score -= tile.score
            self.gone_out = "t"
            self.send_move()
            self.your_turn = False
            self.end_game()
        if self.pass_count >= 2 and pc >= "2":
            for tile in self.tiles_on_rack:
                self.score -= tile.score
            self.gone_out = "t"
            self.send_move()
            self.your_turn = False

    def end_game(self):
        if self.score > self.opponents_score:
            self.result = 1
        elif self.score < self.opponents_score:
            self.result = -1
        else:
            self.result = 0
        self.display_update()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    psutil.Process(os.getpid()).terminate()

    def send_move(self):
        tiles_in_bag = self.create_list_from_tiles_in_bag()
        score = str(self.score)
        tiles_on_board = self.create_list_from_tiles_on_board()
        gone_out = self.gone_out
        pc = str(self.pass_count)

        if self.role == "client":
            data = "c" + tiles_in_bag + "|" + score + "|" + tiles_on_board + "|" + gone_out + "|" + pc
        else:
            data = "h" + tiles_in_bag + "|" + score + "|" + tiles_on_board + "|" + gone_out + "|" + pc
        self.client.send(data.encode())
        self.your_turn = False

    def create_list_from_tiles_on_board(self):
        return ":".join(
            str(tile.rect.x) + "," + str(tile.rect.y) + "," + tile.letter + "," + str(tile.score) for tile in
            self.tiles_on_board)

    def create_tiles_on_board_from_list(self, lst):
        for tile in self.tiles_on_board:
            tile.kill()
        new_lst = lst.split(":")
        for i in new_lst:
            l = i.split(",")
            if int(l[3]) == 0:
                t = Tile(int(l[0]), int(l[1]), "!", int(l[3]))
                t.update(letter=l[2])
                t.add(self.tiles_on_board)
            else:
                Tile(int(l[0]), int(l[1]), l[2], int(l[3])).add(self.tiles_on_board)

    @staticmethod
    def get_ip():
        result = subprocess.run("ipconfig", stdout=subprocess.PIPE, text=True).stdout.lower()
        for i, r in enumerate(result.split("\n")):
            if "default gateway" in r:
                if r.split(":")[1].strip():
                    return result.split("\n")[i-2].split(":")[1].strip()

    def receive_moves(self, conn):
        while True:
            try:
                move = conn.recv(2048).decode()
                if not move:
                    break
                self.opponents_move[move[0]].append(move[1:])
            except:
                break

    def host_game(self):
        self.role = "host"
        self.host_ip = self.get_ip()
        self.host = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host.bind((self.host_ip, 9999))
        self.host.listen(1)
        conn, addr = self.host.accept()
        self.client = conn
        threading.Thread(target=self.receive_moves, args=(conn,), daemon=True).start()

        self.establishing_connection = False
        self.distributing = True
        self.your_turn = True

    def create_list_from_tiles_in_bag(self):
        return "".join([tile.letter for tile in self.tiles_in_bag])

    def create_tiles_in_bag_from_list(self, lst):
        for tile in self.tiles_in_bag:
            tile.kill()
        for l in lst:
            Tile(-50, -50, l, TILES[l][0]).add(self.tiles_in_bag)

    def connect_to_host(self):
        self.role = "client"
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.host_ip, 9999))
        threading.Thread(target=self.receive_moves, args=(self.client,), daemon=True).start()
        self.establishing_connection = False
        self.distributing = True
        self.your_turn = False

    def mouse_click(self, pos):
        if not self.role:
            if self.host_join_buttons["host"][1].collidepoint(pos):
                self.role = "host"
                threading.Thread(target=self.host_game).start()

            if self.host_join_buttons["join"][1].collidepoint(pos):
                self.role = "client"

        for tile in self.tiles_being_swapped:
            if tile.rect.collidepoint(pos):
                tile.remove(self.tiles_being_swapped)
                tile.add(self.tile_in_hand)
                self.remove_arrow()
                return

        if self.your_turn:
            if self.swap_area_rect.collidepoint(pos):
                self.remove_arrow()
                self.exchange_tiles()
                self.send_move()

        for tile in self.tiles_on_rack:
            if tile.rect.collidepoint(pos):
                tile.remove(self.tiles_on_rack)
                tile.add(self.tile_in_hand)
                self.remove_arrow()
                return

        for tile in self.tiles_played:
            if tile.rect.collidepoint(pos):
                tile.remove(self.tiles_played)
                tile.add(self.tile_in_hand)
                self.remove_arrow()
                self.potential_score = None
                self.calculate_score()
                return

        for square in self.gameboard_squares:
            if pygame.sprite.spritecollideany(square, self.tiles_on_board):
                continue
            if square.rect.collidepoint(pos):
                if square.selected:
                    if self.current_arrow == self.across_arrow:
                        self.current_arrow = self.down_arrow
                    else:
                        self.current_arrow = self.across_arrow
                self.remove_arrow()
                square.selected = True
                self.gameboard_squares.update(self.current_arrow)
                return

    def mouse_release(self, pos):
        if self.swap_area_rect.collidepoint(pos):
            tile = self.tile_in_hand.sprite
            if len(self.tiles_being_swapped) < len(self.tiles_in_bag):
                tile.add(self.tiles_being_swapped)
                tile.remove(self.tile_in_hand)
            else:
                self.return_tile_to_rack()
            if tile.score == 0:
                tile.update(letter="!")
            return
        for square in self.gameboard_squares:
            if square.rect.collidepoint(pos):
                if pygame.sprite.spritecollideany(square, self.tiles_played):
                    break
                tile = self.tile_in_hand.sprite
                tile.update(square.rect.center)
                tile.add(self.tiles_played)
                tile.remove(self.tile_in_hand)
                self.calculate_score()
                if tile.letter == "!":
                    self.blank = True
                return
        self.return_tile_to_rack()

    def get_all_words(self):
        self.all_words.clear()
        word_squares = []
        for row in range(TILE_SIZE // 2, TILE_SIZE * 16, TILE_SIZE):
            count = 0
            for square in [s for s in self.gameboard_squares if s.rect.y == row]:
                if pygame.sprite.spritecollideany(square, self.tiles_on_board) or pygame.sprite.spritecollideany(square,
                                                                                                                 self.tiles_played):
                    count += 1
                    if count == 2:
                        word_squares.append((square.rect.x - TILE_SIZE, square.rect.y))
                    if count >= 2:
                        word_squares.append((square.rect.x, square.rect.y))
                else:
                    if count >= 2:
                        word = ""
                        for s in word_squares:
                            for tile in [*self.tiles_on_board, *self.tiles_played]:
                                if tile.rect.topleft == s:
                                    word += tile.letter
                        self.all_words[tuple(word_squares)] = word
                        word_squares.clear()
                        count = 0
                        continue
                    else:
                        count = 0
            if count >= 2:
                word = ""
                for s in word_squares:
                    for tile in [*self.tiles_on_board, *self.tiles_played]:
                        if tile.rect.topleft == s:
                            word += tile.letter
                self.all_words[tuple(word_squares)] = word
                word_squares.clear()

        for col in range(TILE_SIZE, TILE_SIZE * 16, TILE_SIZE):
            count = 0
            for square in [s for s in self.gameboard_squares if s.rect.x == col]:
                if pygame.sprite.spritecollideany(square, self.tiles_on_board) or pygame.sprite.spritecollideany(square,
                                                                                                                 self.tiles_played):
                    count += 1
                    if count == 2:
                        word_squares.append((square.rect.x, square.rect.y - TILE_SIZE))
                    if count >= 2:
                        word_squares.append((square.rect.x, square.rect.y))
                else:
                    if count >= 2:
                        word = ""
                        for s in word_squares:
                            for tile in [*self.tiles_on_board, *self.tiles_played]:
                                if tile.rect.topleft == s:
                                    word += tile.letter
                        self.all_words[tuple(word_squares)] = word
                        word_squares.clear()
                        count = 0
                        continue
                    else:
                        count = 0
            if count >= 2:
                word = ""
                for s in word_squares:
                    for tile in [*self.tiles_on_board, *self.tiles_played]:
                        if tile.rect.topleft == s:
                            word += tile.letter
                self.all_words[tuple(word_squares)] = word
                word_squares.clear()

    def get_words_on_board(self):
        self.words_on_board.clear()
        word_squares = []
        for row in range(TILE_SIZE // 2, TILE_SIZE * 16, TILE_SIZE):
            count = 0
            for square in [s for s in self.gameboard_squares if s.rect.y == row]:
                if pygame.sprite.spritecollideany(square, self.tiles_on_board):
                    count += 1
                    if count == 2:
                        word_squares.append((square.rect.x - TILE_SIZE, square.rect.y))
                    if count >= 2:
                        word_squares.append((square.rect.x, square.rect.y))
                else:
                    if count >= 2:
                        word = ""
                        for s in word_squares:
                            for tile in [*self.tiles_on_board]:
                                if tile.rect.topleft == s:
                                    word += tile.letter
                        self.words_on_board[tuple(word_squares)] = word
                        word_squares.clear()
                        count = 0
                        continue
                    else:
                        count = 0
            if count >= 2:
                word = ""
                for s in word_squares:
                    for tile in [*self.tiles_on_board]:
                        if tile.rect.topleft == s:
                            word += tile.letter
                self.words_on_board[tuple(word_squares)] = word
                word_squares.clear()

        for col in range(TILE_SIZE, TILE_SIZE * 16, TILE_SIZE):
            count = 0
            for square in [s for s in self.gameboard_squares if s.rect.x == col]:
                if pygame.sprite.spritecollideany(square, self.tiles_on_board):
                    count += 1
                    if count == 2:
                        word_squares.append((square.rect.x, square.rect.y - TILE_SIZE))
                    if count >= 2:
                        word_squares.append((square.rect.x, square.rect.y))
                else:
                    if count >= 2:
                        word = ""
                        for s in word_squares:
                            for tile in [*self.tiles_on_board]:
                                if tile.rect.topleft == s:
                                    word += tile.letter
                        self.words_on_board[tuple(word_squares)] = word
                        word_squares.clear()
                        count = 0
                        continue
                    else:
                        count = 0
            if count >= 2:
                word = ""
                for s in word_squares:
                    for tile in [*self.tiles_on_board]:
                        if tile.rect.topleft == s:
                            word += tile.letter
                self.words_on_board[tuple(word_squares)] = word
                word_squares.clear()

    def calculate_score(self):
        self.new_words.clear()
        self.words_on_board.clear()
        self.all_words.clear()
        self.get_words_on_board()
        self.get_all_words()
        for word in self.all_words:
            if word not in self.words_on_board.keys():
                self.new_words[word] = self.all_words[word]
        new_words_pos = [pos for pos in self.all_words if pos not in self.words_on_board]
        if not new_words_pos:
            self.potential_score = 0
            return
        turn_score = 0
        if len(self.tiles_played) == 7:
            turn_score += 50
        for word_pos in new_words_pos:
            word_score = 0
            word_multiplier = 1
            for letter_pos in word_pos:
                for square in self.gameboard_squares:
                    if square.rect.topleft == letter_pos:
                        for tile in self.tiles_played:
                            if tile.rect.topleft == letter_pos:
                                if square.colour == "red":
                                    word_multiplier *= 3
                                elif square.colour == "pink" or square.colour == "pink3":
                                    word_multiplier *= 2
                                elif square.colour == "blue":
                                    for t in self.tiles_played:
                                        if t.rect.topleft == letter_pos:
                                            word_score += t.score * 2
                                            break
                                elif square.colour == "cyan":
                                    for t in self.tiles_played:
                                        if t.rect.topleft == letter_pos:
                                            word_score += t.score
                                            break
                        for tile in list([*self.tiles_on_board, *self.tiles_played]):
                            if tile.rect.topleft == letter_pos:
                                word_score += tile.score
                                break
                        break
            turn_score += word_score * word_multiplier
        if new_words_pos:
            self.potential_score = (
                turn_score,
                (new_words_pos[-1][-1][0] + (TILE_SIZE * 1.25), new_words_pos[-1][-1][1] - (TILE_SIZE * .5)))

    def check_legitimate(self):
        for word in self.new_words.items():
            if word[1].upper() not in ALLOWED_WORDS:
                return False

        rects = [tile.rect.topleft for tile in self.tiles_played]
        if len(set([rect[1] for rect in rects])) == 1:
            start = (min([rect[0] for rect in rects]), rects[0][1])
            end = (max([rect[0] for rect in rects]), rects[0][1])
            for pos in range(start[0], end[0] + TILE_SIZE, TILE_SIZE):
                for square in self.gameboard_squares:
                    if square.rect.topleft == (pos, rects[0][1]):
                        if not pygame.sprite.spritecollideany(square, self.tiles_on_board):
                            if not pygame.sprite.spritecollideany(square, self.tiles_played):
                                return False
                        break

        elif len(set([rect[0] for rect in rects])) == 1:
            start = (rects[0][0], min([rect[1] for rect in rects]))
            end = (rects[0][0], max([rect[1] for rect in rects]))
            for pos in range(start[1], end[1] + TILE_SIZE, TILE_SIZE):
                for square in self.gameboard_squares:
                    if square.rect.topleft == (rects[0][0], pos):
                        if not pygame.sprite.spritecollideany(square, self.tiles_on_board):
                            if not pygame.sprite.spritecollideany(square, self.tiles_played):
                                return False
                        break
        else:
            return False

        positions = []
        for pos in self.new_words.keys():
            for p in pos:
                positions.append(p)
        if not positions:
            return False
        if not (TILE_SIZE * 8, TILE_SIZE * 7.5) in positions:
            if len(positions) == len(self.tiles_played):
                return False
            else:
                return True
        return True

    def delete_last_letter_played(self):
        tile = self.tiles_played.sprites()[-1]
        if tile.score == 0:
            tile.update(letter="!")
        for square in self.gameboard_squares:
            if square.rect == tile.rect:
                square.selected = True
                square.update(self.current_arrow)

        for slot in self.tilerack_slots:
            if pygame.sprite.spritecollideany(slot, self.tiles_on_rack):
                continue
            else:
                tile.update(slot.rect.center)
                tile.add(self.tiles_on_rack)
                tile.remove(self.tiles_played)
                self.calculate_score()

    def return_tile_to_rack(self):
        for slot in self.tilerack_slots:
            if pygame.sprite.spritecollideany(slot, self.tiles_on_rack):
                continue
            else:
                tile = self.tile_in_hand.sprite
                tile.update(slot.rect.center)
                tile.add(self.tiles_on_rack)
                tile.remove(self.tile_in_hand)
                if tile.score == 0:
                    tile.update(letter="!")
                return

    def remove_arrow(self):
        for s in self.gameboard_squares:
            s.selected = False
        self.gameboard_squares.update()

    def move_arrow(self):
        for square in self.gameboard_squares:
            if square.selected:
                square.selected = False
                if self.current_arrow == self.across_arrow:
                    mult = 1
                    for s in self.gameboard_squares:
                        if s.rect.centerx == square.rect.centerx + (
                                TILE_SIZE * mult) and s.rect.centery == square.rect.centery:
                            tile_on_square = False
                            for t in [*self.tiles_on_board, *self.tiles_played]:
                                if t.rect.collidepoint(s.rect.center):
                                    tile_on_square = True
                            if not tile_on_square:
                                s.selected = True
                                s.update(self.current_arrow)
                                return
                            mult += 1
                    return
                else:
                    mult = 1
                    for s in self.gameboard_squares:
                        if s.rect.centery == square.rect.centery + (
                                TILE_SIZE * mult) and s.rect.centerx == square.rect.centerx:
                            tile_on_square = False
                            for t in [*self.tiles_on_board, *self.tiles_played]:
                                if t.rect.collidepoint(s.rect.center):
                                    tile_on_square = True
                            if not tile_on_square:
                                s.selected = True
                                s.update(self.current_arrow)
                                return
                            mult += 1
                    return

    def exchange_tiles(self):
        self.remove_tiles_from_board()
        self.draw_new_tiles()
        if not self.tiles_being_swapped:
            self.pass_count += 1
        else:
            for tile in self.tiles_being_swapped:
                tile.update((-50, -50))
                tile.add(self.tiles_in_bag)
                tile.remove(self.tiles_being_swapped)

    def remove_tiles_from_board(self):
        for tile in self.tiles_played:
            if tile.score == 0:
                tile.update(letter="!")
            for slot in self.tilerack_slots:
                if pygame.sprite.spritecollideany(slot, self.tiles_on_rack):
                    continue
                else:
                    tile.update(slot.rect.center)
                    tile.add(self.tiles_on_rack)
                    tile.remove(self.tiles_played)
                    break

    def remove_tiles_from_swap_area(self):
        for tile in self.tiles_being_swapped:
            for slot in self.tilerack_slots:
                if pygame.sprite.spritecollideany(slot, self.tiles_on_rack):
                    continue
                else:
                    tile.update(slot.rect.center)
                    tile.add(self.tiles_on_rack)
                    tile.remove(self.tiles_being_swapped)
                    break

    def show_potential_score(self):
        surface = pygame.Surface((TILE_SIZE * 1.25, TILE_SIZE * .75), pygame.SRCALPHA, 32).convert_alpha()
        pygame.draw.rect(surface, "white", (0, 0, TILE_SIZE * 1.25, TILE_SIZE * .75), 0, 10)
        pygame.draw.rect(surface, "black", (0, 0, TILE_SIZE * 1.25, TILE_SIZE * .75), 3, 10)
        score_text = self.small_font.render(str(self.potential_score[0]), True, "black")
        surface.blit(score_text, score_text.get_rect(center=surface.get_rect().center))
        self.screen.blit(surface, surface.get_rect(topleft=self.potential_score[1]))

    def show_tooltip(self, region):
        if region == "blank":
            for tile in self.tiles_played:
                if tile.score == 0:
                    rect = tile.rect.topright
                    surface = pygame.Surface((TILE_SIZE * 3, TILE_SIZE * .75), pygame.SRCALPHA, 32).convert_alpha()
                    pygame.draw.rect(surface, "white", (0, 0, TILE_SIZE * 3, TILE_SIZE * .75), 0, 10)
                    pygame.draw.rect(surface, "black", (0, 0, TILE_SIZE * 3, TILE_SIZE * .75), 3, 10)
                    tooltip_text = self.small_font.render("Enter letter", True, "black")
                    surface.blit(tooltip_text, tooltip_text.get_rect(center=surface.get_rect().center))
                    self.screen.blit(surface,
                                     surface.get_rect(topleft=(rect[0] + TILE_SIZE // 10, rect[1] - (TILE_SIZE * .5))))
                    break

        if region == "swap":
            surface = pygame.Surface((TILE_SIZE * 7.5, TILE_SIZE * 2), pygame.SRCALPHA, 32).convert_alpha()
            pygame.draw.rect(surface, "white", (0, 0, TILE_SIZE * 7.5, TILE_SIZE * 2), 0, 10)
            pygame.draw.rect(surface, "black", (0, 0, TILE_SIZE * 7.5, TILE_SIZE * 2), 3, 10)
            tooltip_text = self.small_font.render("Drop tiles to swap here,", True, "black")
            tooltip_text_2 = self.small_font.render("then click to swap tiles.", True, "black")
            tooltip_text_3 = self.small_font.render("(Click while empty to pass.)", True, "black")
            surface.blit(tooltip_text, tooltip_text.get_rect(center=(surface.get_rect().centerx, TILE_SIZE // 2)))
            surface.blit(tooltip_text_2, tooltip_text_2.get_rect(center=(surface.get_rect().centerx, TILE_SIZE)))
            surface.blit(tooltip_text_3, tooltip_text_3.get_rect(center=(surface.get_rect().centerx, TILE_SIZE * 1.5)))
            self.screen.blit(surface, surface.get_rect(midbottom=pygame.mouse.get_pos()))

    def draw_new_tiles(self):
        for slot in self.tilerack_slots:
            if not self.tiles_in_bag:
                break
            if pygame.sprite.spritecollideany(slot, self.tiles_on_rack):
                continue
            else:
                tile = random.choice(list(self.tiles_in_bag))
                tile.remove(self.tiles_in_bag)
                tile.update(slot.rect.center)
                tile.add(self.tiles_on_rack)

    def create_game_mode_buttons(self):
        host_button = pygame.Surface((TILE_SIZE * 10, TILE_SIZE * 10))
        host_button_rect = host_button.get_rect(center=(self.screen.get_width() // 4, self.screen.get_height() // 2))
        join_button = pygame.Surface((TILE_SIZE * 10, TILE_SIZE * 10))
        join_button_rect = host_button.get_rect(
            center=(self.screen.get_width() // 4 * 3, self.screen.get_height() // 2))
        hb_text = self.panel_font.render("Host Game", True, "black")
        hb_text_rect = hb_text.get_rect(center=host_button.get_rect().center)
        jb_text = self.panel_font.render("Join Game", True, "black")
        jb_text_rect = jb_text.get_rect(center=join_button.get_rect().center)
        host_button.fill("pink")
        join_button.fill("cyan")
        host_button.blit(hb_text, hb_text_rect)
        join_button.blit(jb_text, jb_text_rect)
        self.host_join_buttons["host"] = (host_button, host_button_rect)
        self.host_join_buttons["join"] = (join_button, join_button_rect)

    def display_update(self):
        self.screen.fill("green")
        self.screen.blit(self.title, self.title_rect)
        if self.establishing_connection:
            if self.role == "client":
                msg = self.panel_font.render("Enter host ip address...", True, "black")
                inp = self.panel_font.render(self.host_ip, True, "black")
                self.screen.blit(msg, (10, 10))
                self.screen.blit(inp, (10, 50))

            elif self.role == "host":
                msg = self.panel_font.render("Waiting for client...", True, "black")
                self.screen.blit(msg, (10, 10))
                msg = self.panel_font.render(f"Host ip address: {self.host_ip}", True, "black")
                self.screen.blit(msg, (10, 50))

            else:
                self.create_game_mode_buttons()
                self.screen.blit(self.host_join_buttons["host"][0], self.host_join_buttons["host"][1])
                self.screen.blit(self.host_join_buttons["join"][0], self.host_join_buttons["join"][1])

        else:
            self.bag.fill("darkgreen")
            score_text = self.panel_font.render(f"Your score: {self.score}", True, "black")
            score_text_rect = score_text.get_rect(center=(self.bag.get_width() // 2, self.bag.get_height() // 5))
            opp_score_text = self.panel_font.render(f"Opponents score: {self.opponents_score}", True, "black")
            opp_score_text_rect = opp_score_text.get_rect(
                center=(self.bag.get_width() // 2, self.bag.get_height() // 5 * 2))
            bag_text = self.small_font.render(f"{len(self.tiles_in_bag)} tiles remaining", True, "black")
            bag_text_rect = bag_text.get_rect(center=(self.bag.get_width() // 2, self.bag.get_height() // 5 * 4))
            if self.result == 1:
                turn_txt = "You Won!"
            elif self.result == -1:
                turn_txt = "You Lost!"
            elif self.result == 0:
                turn_txt = "It's a Draw!"
            elif self.your_turn:
                turn_txt = "Your turn."
            else:
                turn_txt = "Opponent's turn"
            turn_text = self.panel_font.render(turn_txt, True, "white")
            turn_text_rect = turn_text.get_rect(center=(self.bag.get_width() // 2, self.bag.get_height() // 5 * 3))
            self.bag.blit(bag_text, bag_text_rect)
            self.bag.blit(score_text, score_text_rect)
            self.bag.blit(opp_score_text, opp_score_text_rect)
            self.bag.blit(turn_text, turn_text_rect)
            self.screen.blit(self.bag, self.bag_rect)

            self.swap_area.fill("darkgreen")
            swap_text = self.panel_font.render("Exchange / Pass", True, "black")
            swap_text_rect = swap_text.get_rect(center=(self.swap_area.get_width() // 2, TILE_SIZE))
            swap_text2 = self.small_font.render("Place tiles to discard here.", True, "black")
            swap_text2_rect = swap_text2.get_rect(center=(self.swap_area.get_width() // 2, TILE_SIZE * 2))
            self.swap_area.blit(swap_text, swap_text_rect)
            self.swap_area.blit(swap_text2, swap_text2_rect)
            self.screen.blit(self.swap_area, self.swap_area_rect)

            self.screen.blit(self.tilerack, self.tilerack_rect)

            self.gameboard_squares.draw(self.screen)
            self.tilerack_slots.draw(self.screen)
            self.tiles_on_rack.draw(self.screen)
            self.tiles_on_board.draw(self.screen)
            self.tiles_played.draw(self.screen)
            self.tiles_being_swapped.draw(self.screen)
            self.tile_in_hand.draw(self.screen)

            if self.potential_score:
                self.show_potential_score()

            if self.blank:
                self.show_tooltip("blank")

            if self.swap_area_tooltip:
                self.show_tooltip("swap")
        pygame.display.update()


if __name__ == '__main__':
    game = Game()
    print(TILERACK_SLOTS)
    game.run()