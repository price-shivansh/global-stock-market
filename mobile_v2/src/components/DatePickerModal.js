import React from 'react';
import { View, Text, Modal, TouchableOpacity, StyleSheet, FlatList } from 'react-native';
import { COLORS, SIZES, FONTS } from '../constants/theme';

const DatePickerModal = ({ visible, dates, onClose, onSelectDate }) => {
  return (
    <Modal visible={visible} transparent animationType="slide">
      <View style={styles.overlay}>
        <View style={styles.modalContainer}>
          <View style={styles.header}>
            <Text style={styles.title}>SELECT ARCHIVE DATE</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
              <Text style={styles.closeText}>X</Text>
            </TouchableOpacity>
          </View>
          
          {(!dates || dates.length === 0) ? (
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyText}>No historical dates available.</Text>
            </View>
          ) : (
            <FlatList
              data={dates}
              keyExtractor={(item) => item}
              renderItem={({ item }) => (
                <TouchableOpacity 
                  style={styles.dateItem}
                  onPress={() => onSelectDate(item)}
                >
                  <Text style={styles.dateText}>{item}</Text>
                </TouchableOpacity>
              )}
              ItemSeparatorComponent={() => <View style={styles.separator} />}
            />
          )}
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'flex-end',
  },
  modalContainer: {
    backgroundColor: COLORS.cardBackground,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    minHeight: '40%',
    maxHeight: '80%',
    padding: SIZES.md,
    borderTopWidth: 1,
    borderColor: COLORS.border,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.md,
    paddingBottom: SIZES.sm,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  title: {
    color: COLORS.primary,
    fontFamily: FONTS.mono,
    fontSize: SIZES.md,
  },
  closeButton: {
    padding: 8,
  },
  closeText: {
    color: COLORS.textMuted,
    fontFamily: FONTS.bold,
    fontSize: SIZES.md,
  },
  dateItem: {
    paddingVertical: SIZES.md,
  },
  dateText: {
    color: COLORS.text,
    fontSize: SIZES.md,
    fontFamily: FONTS.regular,
    textAlign: 'center',
  },
  separator: {
    height: 1,
    backgroundColor: COLORS.border,
  },
  emptyContainer: {
    padding: SIZES.xl,
    alignItems: 'center',
  },
  emptyText: {
    color: COLORS.textMuted,
  },
});

export default DatePickerModal;
