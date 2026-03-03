#!/usr/bin/env python3
"""
Teknofest Hava Savunma Sistemi - State Machine Runner
3 Aşamalı Yarışma Desteği

State'leri farklı dosyalardan dinamik olarak import eder ve yönetir.
"""

import importlib
from typing import Dict, Any, Optional
from . import State, CompetitionStage


class StateMachine:
    """
    Gelişmiş State Machine
    
    3 farklı yarışma aşamasını destekler:
    - Aşama 1: Durağan Hedef İmhası
    - Aşama 2: Sürü Saldırısı
    - Aşama 3: Hareketli Hedefler
    
    Her state için ayrı bir dosya kullanır.
    """
    
    def __init__(self, initial_state: State = State.IDLE):
        """
        State Machine başlat.
        
        Args:
            initial_state: Başlangıç state'i
        """
        self.current_state = initial_state
        self.previous_state: Optional[State] = None
        self.context: Dict[str, Any] = {}  # Paylaşılan veriler
        self.current_stage: Optional[CompetitionStage] = None
        self._state_modules: Dict[State, Any] = {}
        self._stage_modules: Dict[CompetitionStage, Any] = {}
    
    def set_stage(self, stage: CompetitionStage) -> None:
        """
        Yarışma aşamasını ayarla.
        
        Args:
            stage: Yarışma aşaması (STAGE_1, STAGE_2, STAGE_3)
        """
        self.current_stage = stage
        print(f">>> Yarışma Aşaması: {stage.name}")
        
        # Aşamaya göre başlangıç state'i ayarla
        initial_states = {
            CompetitionStage.STAGE_1: State.STAGE1_WAITING_ORDER,
            CompetitionStage.STAGE_2: State.STAGE2_SCANNING,
            CompetitionStage.STAGE_3: State.STAGE3_DETECTING,
        }
        
        self.current_state = initial_states.get(stage, State.IDLE)
        self.context['current_state'] = self.current_state
        self.context['competition_stage'] = stage
    
    def _load_state_module(self, state: State):
        """State modülünü yükle (eski sistemle uyumluluk için)"""
        if state not in self._state_modules:
            module_name = f".state_{state.value}"
            try:
                module = importlib.import_module(module_name, package="hava_savunma_pkg.state_machine")
                self._state_modules[state] = module
            except ImportError as e:
                # Yeni stage modüllerini dene
                return None
        return self._state_modules.get(state)
    
    def _load_stage_module(self, stage: CompetitionStage):
        """Stage modülünü yükle"""
        if stage not in self._stage_modules:
            stage_names = {
                CompetitionStage.STAGE_1: "stage1_states",
                CompetitionStage.STAGE_2: "stage2_states",
                CompetitionStage.STAGE_3: "stage3_states",
            }
            
            module_name = f".{stage_names.get(stage)}"
            try:
                module = importlib.import_module(module_name, package="hava_savunma_pkg.state_machine")
                self._stage_modules[stage] = module
            except ImportError as e:
                print(f"HATA: {stage.name} modülü yüklenemedi: {e}")
                return None
        return self._stage_modules.get(stage)
    
    def update(self) -> State:
        """
        Mevcut state'i çalıştır ve gerekirse geçiş yap.
        
        Returns:
            Mevcut state
        """
        next_state_name = None
        self.context['current_state'] = self.current_state
        
        # Önce stage modüllerini dene
        if self.current_stage:
            module = self._load_stage_module(self.current_stage)
            if module and hasattr(module, 'execute'):
                next_state_name = module.execute(self.context)
        
        # Eski sistemle uyumluluk (scanning, detected vb.)
        if not next_state_name:
            module = self._load_state_module(self.current_state)
            if module and hasattr(module, 'execute'):
                next_state_name = module.execute(self.context)
        
        # State geçişi
        if next_state_name:
            try:
                new_state = State[next_state_name]
                if new_state != self.current_state:
                    self.previous_state = self.current_state
                    print(f">>> State değişti: {self.current_state.name} -> {new_state.name}")
                    self.current_state = new_state
                    self.context['current_state'] = new_state
            except KeyError:
                print(f"HATA: Geçersiz state: {next_state_name}")
        
        return self.current_state
    
    def transition_to(self, new_state: State) -> None:
        """
        Belirli bir state'e geçiş yap.
        
        Args:
            new_state: Hedef state
        """
        if new_state != self.current_state:
            self.previous_state = self.current_state
            self.current_state = new_state
            self.context['current_state'] = new_state
            print(f">>> State değişti: {self.previous_state.name} -> {new_state.name}")
    
    def set_frame(self, frame) -> None:
        """Kamera görüntüsünü ayarla"""
        self.context['frame'] = frame
    
    def start(self) -> None:
        """Sistemi başlat"""
        self.context['start_command'] = True
    
    def stop(self) -> None:
        """Sistemi durdur"""
        self.context['start_command'] = False
        self.context['continue_scanning'] = False
    
    def get_balloons(self) -> Dict[str, list]:
        """Tespit edilen balonları döndür (geriye uyumluluk)"""
        return self.context.get('balloons', {'red': [], 'blue': []})
    
    def get_context(self) -> Dict[str, Any]:
        """Tüm context'i döndür"""
        return self.context
    
    def set_context(self, key: str, value: Any) -> None:
        """Context değeri ayarla"""
        self.context[key] = value
    
    def is_completed(self) -> bool:
        """Tamamlandı mı kontrol et"""
        return self.current_state == State.COMPLETED
    
    def has_error(self) -> bool:
        """Hata var mı kontrol et"""
        return self.current_state == State.ERROR
    
    def reset(self) -> None:
        """State machine'i sıfırla"""
        self.current_state = State.IDLE
        self.previous_state = None
        self.current_stage = None
        self.context = {}
        print(">>> State Machine sıfırlandı")

