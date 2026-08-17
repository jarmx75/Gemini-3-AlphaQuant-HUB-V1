"""
Backup Manager Module
Sistema de respaldos automatizados para el proyecto.
"""

import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
import logging
import gzip
import tarfile
from typing import List
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackupManager:
    """Gestor de respaldos automatizados."""
    
    def __init__(
        self,
        project_root: str,
        backup_dir: str = 'backups',
        retention_days: int = 30
    ):
        """
        Inicializar gestor de backups.
        
        Args:
            project_root: Directorio raíz del proyecto
            backup_dir: Directorio de backups
            retention_days: Días de retención de backups
        """
        self.project_root = Path(project_root)
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"BackupManager inicializado: {self.backup_dir}")
    
    def create_full_backup(self) -> str:
        """
        Crear backup completo del proyecto.
        
        Returns:
            Ruta del backup creado
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"trading_system_full_{timestamp}.tar.gz"
        backup_path = self.backup_dir / backup_name
        
        # Directorios a incluir en el backup
        dirs_to_backup = [
            'src',
            'config',
            'data',
            'docs',
            'notebooks'
        ]
        
        try:
            with tarfile.open(backup_path, 'w:gz') as tar:
                for dir_name in dirs_to_backup:
                    dir_path = self.project_root / dir_name
                    if dir_path.exists():
                        tar.add(dir_path, arcname=dir_name)
                        logger.info(f"Añadido al backup: {dir_name}")
                
                # Añadir README
                readme_path = self.project_root / 'README.md'
                if readme_path.exists():
                    tar.add(readme_path, arcname='README.md')
            
            logger.info(f"Backup completo creado: {backup_path}")
            logger.info(f"Tamaño: {backup_path.stat().st_size / (1024*1024):.2f} MB")
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Error creando backup completo: {e}")
            return ""
    
    def create_database_backup(self, db_path: str) -> str:
        """
        Crear backup específico de la base de datos.
        
        Args:
            db_path: Ruta de la base de datos
            
        Returns:
            Ruta del backup creado
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        db_file = Path(db_path)
        backup_name = f"{db_file.stem}_{timestamp}.db"
        backup_path = self.backup_dir / 'databases' / backup_name
        
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Método 1: Usar SQLite backup API (más seguro)
            source = sqlite3.connect(str(db_file))
            dest = sqlite3.connect(str(backup_path))
            
            with dest:
                source.backup(dest)
            
            source.close()
            dest.close()
            
            logger.info(f"Backup de base de datos creado: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Error creando backup de DB: {e}")
            # Fallback: copia simple
            try:
                shutil.copy2(db_file, backup_path)
                logger.info(f"Backup de DB creado (copia simple): {backup_path}")
                return str(backup_path)
            except Exception as e2:
                logger.error(f"Error en fallback: {e2}")
                return ""
    
    def create_config_backup(self) -> str:
        """
        Crear backup de configuraciones.
        
        Returns:
            Ruta del backup creado
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"config_{timestamp}.tar.gz"
        backup_path = self.backup_dir / 'configs' / backup_name
        
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            config_dir = self.project_root / 'config'
            if config_dir.exists():
                with tarfile.open(backup_path, 'w:gz') as tar:
                    tar.add(config_dir, arcname='config')
                
                logger.info(f"Backup de configuración creado: {backup_path}")
                return str(backup_path)
            else:
                logger.warning("Directorio config no encontrado")
                return ""
                
        except Exception as e:
            logger.error(f"Error creando backup de config: {e}")
            return ""
    
    def clean_old_backups(self) -> int:
        """
        Eliminar backups antiguos según política de retención.
        
        Returns:
            Número de backups eliminados
        """
        deleted_count = 0
        cutoff_date = datetime.now().timestamp() - (self.retention_days * 24 * 60 * 60)
        
        try:
            for backup_file in self.backup_dir.rglob('*'):
                if backup_file.is_file() and backup_file.stat().st_mtime < cutoff_date:
                    backup_file.unlink()
                    deleted_count += 1
                    logger.info(f"Backup antiguo eliminado: {backup_file}")
            
            logger.info(f"Limpiados {deleted_count} backups antiguos")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error limpiando backups antiguos: {e}")
            return 0
    
    def list_backups(self) -> List[dict]:
        """
        Listar todos los backups disponibles.
        
        Returns:
            Lista de dicts con información de backups
        """
        backups = []
        
        try:
            for backup_file in self.backup_dir.rglob('*'):
                if backup_file.is_file():
                    stat = backup_file.stat()
                    backups.append({
                        'path': str(backup_file),
                        'size_mb': stat.st_size / (1024 * 1024),
                        'created': datetime.fromtimestamp(stat.st_mtime),
                        'type': 'full' if 'full' in backup_file.name else 'partial'
                    })
            
            # Ordenar por fecha (más reciente primero)
            backups.sort(key=lambda x: x['created'], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Error listando backups: {e}")
            return []
    
    def restore_backup(self, backup_path: str, restore_dir: str) -> bool:
        """
        Restaurar backup desde archivo.
        
        Args:
            backup_path: Ruta del backup a restaurar
            restore_dir: Directorio donde restaurar
            
        Returns:
            True si exitoso
        """
        try:
            restore_path = Path(restore_dir)
            restore_path.mkdir(parents=True, exist_ok=True)
            
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(restore_path)
            
            logger.info(f"Backup restaurado en: {restore_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error restaurando backup: {e}")
            return False
    
    def create_daily_backup(self) -> dict:
        """
        Crear backup diario completo (automatizado).
        
        Returns:
            Dict con rutas de backups creados
        """
        logger.info("Iniciando backup diario...")
        
        results = {
            'full_backup': self.create_full_backup(),
            'database_backup': None,
            'config_backup': None,
            'cleaned': self.clean_old_backups()
        }
        
        # Backup específico de base de datos si existe
        db_path = self.project_root / 'data' / 'trading.db'
        if db_path.exists():
            results['database_backup'] = self.create_database_backup(str(db_path))
        
        # Backup de configuración
        results['config_backup'] = self.create_config_backup()
        
        logger.info(f"Backup diario completado: {results}")
        return results


def main():
    """Función principal para testing."""
    import os
    
    # Obtener directorio del proyecto
    project_root = Path(__file__).parent.parent.parent
    
    # Crear gestor de backups
    backup_manager = BackupManager(
        project_root=str(project_root),
        backup_dir=str(project_root / 'backups'),
        retention_days=7  # 7 días para testing
    )
    
    # Crear backup diario
    results = backup_manager.create_daily_backup()
    
    print("\nResultados del backup:")
    for key, value in results.items():
        print(f"{key}: {value}")
    
    # Listar backups
    print("\nBackups disponibles:")
    backups = backup_manager.list_backups()
    for backup in backups[:5]:  # Mostrar primeros 5
        print(f"  {backup['created']} - {backup['path']} ({backup['size_mb']:.2f} MB)")


if __name__ == '__main__':
    main()
