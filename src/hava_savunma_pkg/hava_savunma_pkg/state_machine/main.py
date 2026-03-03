#!/usr/bin/env python3
"""
Teknofest Hava Savunma Sistemi - Ana Kontrolcü

Bu dosya yarışmanın 3 aşaması için ana kontrolcü sınıfını içerir.
Her aşama bağımsız olarak çalıştırılabilir.

Kullanım:
    controller = CompetitionController()
    
    # Aşama 1
    controller.run_stage1(target_order=[1, 3, 2, 5, 4])
    
    # Aşama 2
    controller.run_stage2()
    
    # Aşama 3
    controller.run_stage3()
    
    # Sonuçlar
    results = controller.get_all_results()
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from . import State, CompetitionStage, Target, TargetType, TargetFaction
from .stage1_states import Stage1Context, get_stage1_results
from .stage2_states import Stage2Context, get_stage2_results
from .stage3_states import Stage3Context, get_stage3_results


@dataclass
class CompetitionResults:
    """Yarışma sonuçları"""
    stage1_score: int = 0
    stage1_penalty: int = 0
    stage2_score: int = 0
    stage3_score: int = 0
    stage3_penalty: int = 0
    total_score: int = 0
    
    def calculate_total(self):
        """Toplam skoru hesapla"""
        self.total_score = (
            (self.stage1_score - self.stage1_penalty) +
            self.stage2_score +
            (self.stage3_score - self.stage3_penalty)
        )


class CompetitionController:
    """
    Yarışma Ana Kontrolcüsü
    
    3 aşamalı yarışma için merkezi kontrol sınıfı.
    Her aşamayı yönetir ve sonuçları toplar.
    """
    
    def __init__(self):
        """Kontrolcüyü başlat"""
        self.current_stage: Optional[CompetitionStage] = None
        self.current_state: State = State.IDLE
        self.context: Dict[str, Any] = {}
        self.results = CompetitionResults()
        self.is_running = False
        
        # State modülleri
        self._stage_modules = {}
        
        print("="*60)
        print("  TEKNOFEST HAVA SAVUNMA SİSTEMİ")
        print("  Yarışma Kontrolcüsü Başlatıldı")
        print("="*60)
    
    # =========================================================================
    # AŞAMA 1: DURAĞAN HEDEF İMHASI
    # =========================================================================
    
    def run_stage1(self, target_order: List[int], 
                   target_positions: Optional[Dict[int, tuple]] = None,
                   target_distances: Optional[Dict[int, float]] = None) -> Dict[str, Any]:
        """
        Aşama 1'i çalıştır: Farklı Menzillerde Duran Hedef İmhası
        
        Args:
            target_order: Zarf ile verilen hedef sırası [1, 3, 2, 5, 4]
            target_positions: Hedef pozisyonları {id: (x, y, z)}
            target_distances: Hedef mesafeleri {id: distance_m}
        
        Returns:
            Aşama 1 sonuçları
        """
        print("\n" + "="*60)
        print("  AŞAMA 1: FARKLI MENZİLLERDE DURAN HEDEF İMHASI")
        print("="*60)
        print(f"  Hedef Sırası: {target_order}")
        print("="*60 + "\n")
        
        self.current_stage = CompetitionStage.STAGE_1
        self.current_state = State.STAGE1_WAITING_ORDER
        
        # Context hazırla
        stage1_ctx = Stage1Context(
            target_order=target_order,
            target_positions=target_positions or {},
            target_distances=target_distances or {i: 10.0 for i in target_order}
        )
        self.context['stage1'] = stage1_ctx
        self.context['current_state'] = self.current_state
        
        # State machine döngüsü
        self.is_running = True
        
        while self.is_running:
            next_state = self._execute_stage1_state()
            
            if next_state:
                try:
                    new_state = State[next_state]
                    if new_state != self.current_state:
                        print(f">>> State: {self.current_state.name} -> {new_state.name}")
                        self.current_state = new_state
                        self.context['current_state'] = new_state
                except KeyError:
                    print(f"HATA: Geçersiz state: {next_state}")
            
            # Tamamlandı mı?
            if self.current_state in [State.COMPLETED, State.ERROR]:
                self.is_running = False
            
            time.sleep(0.1)  # 100ms döngü
        
        # Sonuçları kaydet
        results = get_stage1_results(self.context)
        self.results.stage1_score = results['score']
        self.results.stage1_penalty = results['penalty']
        
        print("\n" + "="*60)
        print("  AŞAMA 1 TAMAMLANDI")
        print(f"  Skor: {results['score']} | Ceza: {results['penalty']}")
        print(f"  Net: {results['net_score']}")
        print("="*60 + "\n")
        
        return results
    
    def _execute_stage1_state(self) -> Optional[str]:
        """Aşama 1 state'ini çalıştır"""
        from . import stage1_states
        
        state_map = {
            State.STAGE1_WAITING_ORDER: stage1_states.execute_waiting_order,
            State.STAGE1_AIMING: stage1_states.execute_aiming,
            State.STAGE1_FIRING: stage1_states.execute_firing,
            State.STAGE1_VERIFYING: stage1_states.execute_verifying,
            State.STAGE1_NEXT_TARGET: stage1_states.execute_next_target,
        }
        
        handler = state_map.get(self.current_state)
        if handler:
            return handler(self.context)
        return None
    
    # =========================================================================
    # AŞAMA 2: SÜRÜ SALDIRISI
    # =========================================================================
    
    def run_stage2(self, max_rounds: int = 5) -> Dict[str, Any]:
        """
        Aşama 2'yi çalıştır: Sürü Saldırısı ve İmhası
        
        Args:
            max_rounds: Maksimum tur sayısı
        
        Returns:
            Aşama 2 sonuçları
        """
        print("\n" + "="*60)
        print("  AŞAMA 2: SÜRÜ SALDIRISI VE İMHASI")
        print("="*60)
        print(f"  Maksimum Tur: {max_rounds}")
        print("="*60 + "\n")
        
        self.current_stage = CompetitionStage.STAGE_2
        self.current_state = State.STAGE2_SCANNING
        
        # Context hazırla
        stage2_ctx = Stage2Context(max_rounds=max_rounds)
        self.context['stage2'] = stage2_ctx
        self.context['current_state'] = self.current_state
        
        # State machine döngüsü
        self.is_running = True
        
        while self.is_running:
            next_state = self._execute_stage2_state()
            
            if next_state:
                try:
                    new_state = State[next_state]
                    if new_state != self.current_state:
                        print(f">>> State: {self.current_state.name} -> {new_state.name}")
                        self.current_state = new_state
                        self.context['current_state'] = new_state
                except KeyError:
                    print(f"HATA: Geçersiz state: {next_state}")
            
            if self.current_state in [State.COMPLETED, State.ERROR]:
                self.is_running = False
            
            time.sleep(0.1)
        
        # Sonuçları kaydet
        results = get_stage2_results(self.context)
        self.results.stage2_score = results['score']
        
        print("\n" + "="*60)
        print("  AŞAMA 2 TAMAMLANDI")
        print(f"  Skor: {results['score']}")
        print(f"  Toplam İmha: {results['total_destroyed']}")
        print("="*60 + "\n")
        
        return results
    
    def _execute_stage2_state(self) -> Optional[str]:
        """Aşama 2 state'ini çalıştır"""
        from . import stage2_states
        
        state_map = {
            State.STAGE2_SCANNING: stage2_states.execute_scanning,
            State.STAGE2_TRACKING: stage2_states.execute_tracking,
            State.STAGE2_PRIORITIZING: stage2_states.execute_prioritizing,
            State.STAGE2_ENGAGING: stage2_states.execute_engaging,
            State.STAGE2_ROUND_COMPLETE: stage2_states.execute_round_complete,
        }
        
        handler = state_map.get(self.current_state)
        if handler:
            return handler(self.context)
        return None
    
    # =========================================================================
    # AŞAMA 3: HAREKETLİ HEDEFLER
    # =========================================================================
    
    def run_stage3(self, max_rounds: int = 10) -> Dict[str, Any]:
        """
        Aşama 3'ü çalıştır: Farklı Katmanlardaki Hareketli Hedeflerin İmhası
        
        Args:
            max_rounds: Maksimum tur sayısı (varsayılan 10)
        
        Returns:
            Aşama 3 sonuçları
        """
        print("\n" + "="*60)
        print("  AŞAMA 3: HAREKETLİ HEDEFLERİN İMHASI")
        print("="*60)
        print(f"  Maksimum Tur: {max_rounds}")
        print("  Kural: Her turda 1 düşman + 2 dost")
        print("  Ceza: Dost vurma = 10 puan")
        print("  Başarısızlık: 4 tur ardışık düşman vuramama")
        print("="*60 + "\n")
        
        self.current_stage = CompetitionStage.STAGE_3
        self.current_state = State.STAGE3_DETECTING
        
        # Context hazırla
        stage3_ctx = Stage3Context(max_rounds=max_rounds)
        self.context['stage3'] = stage3_ctx
        self.context['current_state'] = self.current_state
        
        # State machine döngüsü
        self.is_running = True
        
        while self.is_running:
            next_state = self._execute_stage3_state()
            
            if next_state:
                try:
                    new_state = State[next_state]
                    if new_state != self.current_state:
                        print(f">>> State: {self.current_state.name} -> {new_state.name}")
                        self.current_state = new_state
                        self.context['current_state'] = new_state
                except KeyError:
                    print(f"HATA: Geçersiz state: {next_state}")
            
            if self.current_state in [State.COMPLETED, State.ERROR]:
                self.is_running = False
            
            time.sleep(0.1)
        
        # Sonuçları kaydet
        results = get_stage3_results(self.context)
        self.results.stage3_score = results['score']
        self.results.stage3_penalty = results['penalty']
        
        status = "BAŞARILI" if not results['is_failed'] else "BAŞARISIZ"
        
        print("\n" + "="*60)
        print(f"  AŞAMA 3 {status}")
        print(f"  Skor: {results['score']} | Ceza: {results['penalty']}")
        print(f"  Net: {results['net_score']}")
        print("="*60 + "\n")
        
        return results
    
    def _execute_stage3_state(self) -> Optional[str]:
        """Aşama 3 state'ini çalıştır"""
        from . import stage3_states
        
        state_map = {
            State.STAGE3_DETECTING: stage3_states.execute_detecting,
            State.STAGE3_CLASSIFYING: stage3_states.execute_classifying,
            State.STAGE3_ENGAGING_ENEMY: stage3_states.execute_engaging_enemy,
            State.STAGE3_VERIFYING: stage3_states.execute_verifying,
            State.STAGE3_ROUND_COMPLETE: stage3_states.execute_round_complete,
        }
        
        handler = state_map.get(self.current_state)
        if handler:
            return handler(self.context)
        return None
    
    # =========================================================================
    # SONUÇLAR VE YARDIMCI METODLAR
    # =========================================================================
    
    def get_all_results(self) -> Dict[str, Any]:
        """Tüm aşamaların sonuçlarını döndür"""
        self.results.calculate_total()
        
        return {
            'stage1': {
                'score': self.results.stage1_score,
                'penalty': self.results.stage1_penalty,
                'net': self.results.stage1_score - self.results.stage1_penalty,
            },
            'stage2': {
                'score': self.results.stage2_score,
            },
            'stage3': {
                'score': self.results.stage3_score,
                'penalty': self.results.stage3_penalty,
                'net': self.results.stage3_score - self.results.stage3_penalty,
            },
            'total_score': self.results.total_score,
        }
    
    def stop(self):
        """Yarışmayı durdur"""
        self.is_running = False
        print("[KONTROLCÜ] Yarışma durduruldu.")
    
    def reset(self):
        """Yarışmayı sıfırla"""
        self.current_stage = None
        self.current_state = State.IDLE
        self.context = {}
        self.results = CompetitionResults()
        self.is_running = False
        print("[KONTROLCÜ] Yarışma sıfırlandı.")
    
    def get_current_state(self) -> State:
        """Mevcut state'i döndür"""
        return self.current_state
    
    def get_current_stage(self) -> Optional[CompetitionStage]:
        """Mevcut aşamayı döndür"""
        return self.current_stage


# ============================================================================
# TEST FONKSİYONU
# ============================================================================

def run_demo():
    """Demo çalıştır"""
    controller = CompetitionController()
    
    # Aşama 1 demo
    print("\n>>> DEMO: Aşama 1 başlatılıyor...")
    # Not: Gerçek hedefler olmadan state machine hemen tamamlanacak
    # Gerçek implementasyonda hedef algılama sistemi bağlanmalı
    
    # Sadece yapıyı test et
    controller.reset()
    print("\n>>> Demo tamamlandı. State machine yapısı hazır.")
    print(">>> Gerçek kullanım için hedef algılama sistemini bağlayın.")


if __name__ == '__main__':
    run_demo()
