import logging
import math
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

# Включим логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Определяем состояния для ConversationHandler
FULFILLMENT_TYPE, NAME, DIMENSIONS, QUANTITY, BOX_CHOICE, CUSTOM_BOX, COST, TIME, AVG_ORDERS = range(9)

# Константы
HOURLY_RATE = 350
MARKUP = 200 / 100
FBO_DISCOUNT = 0.1  # Скидка 10% для ФБО

# Начало диалога с кнопками
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [KeyboardButton("ФБС"), KeyboardButton("ФБО")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "📦 *Калькулятор стоимости упаковки*\n\n"
        "Выберите тип фулфилмента:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return FULFILLMENT_TYPE

# Обработка выбора типа фулфилмента
async def fulfillment_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    
    if choice not in ["ФБС", "ФБО"]:
        keyboard = [[KeyboardButton("ФБС"), KeyboardButton("ФБО")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "Пожалуйста, выберите один из вариантов:",
            reply_markup=reply_markup
        )
        return FULFILLMENT_TYPE
    
    context.user_data['fulfillment_type'] = choice
    
    if choice == "ФБС":
        await update.message.reply_text(
            "Введите название товара:",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return NAME
    else:  # ФБО
        await update.message.reply_text(
            "Введите габариты товара в мм (ДxШxВ через пробел):\n"
            "Например: 150 100 200",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return DIMENSIONS

# Получаем название товара для ФБС
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Отмена":
        return await cancel(update, context)
    
    context.user_data["item_name"] = update.message.text
    
    if context.user_data['fulfillment_type'] == "ФБС":
        await update.message.reply_text(
            "💰 Введите себестоимость упаковки товара в рублях:\n"
            "Например: 25.50",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return COST
    else:  # ФБО
        # После ввода названия для ФБО переходим к выбору коробки
        keyboard = [
            [KeyboardButton("Коробка 600x400x400")],
            [KeyboardButton("Ввести размеры коробки вручную")],
            [KeyboardButton("Отмена")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await update.message.reply_text(
            "📦 Выберите коробку для упаковки:",
            reply_markup=reply_markup
        )
        return BOX_CHOICE

# Получаем габариты для ФБО
async def get_dimensions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Отмена":
        return await cancel(update, context)
    
    try:
        dimensions = list(map(float, update.message.text.strip().split()))
        if len(dimensions) != 3:
            raise ValueError
        
        for dim in dimensions:
            if dim <= 0:
                raise ValueError
        
        context.user_data["dimensions"] = dimensions
        
        await update.message.reply_text(
            "📊 Введите размер партии (количество штук):\n"
            "Например: 100",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return QUANTITY
        
    except:
        await update.message.reply_text(
            "❌ Неверный формат! Введите три положительных числа через пробел:\n"
            "Например: 150 100 200",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return DIMENSIONS

# Получаем количество товара для ФБО
async def get_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Отмена":
        return await cancel(update, context)
    
    try:
        quantity = int(update.message.text)
        if quantity <= 0:
            raise ValueError
        
        context.user_data["quantity"] = quantity
        
        await update.message.reply_text(
            "Введите название товара:",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return NAME
        
    except:
        await update.message.reply_text(
            "❌ Введите целое положительное число:\n"
            "Например: 100",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return QUANTITY

# Обработка выбора коробки
async def box_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    
    if choice == "Отмена":
        return await cancel(update, context)
    
    if choice == "Коробка 600x400x400":
        context.user_data["box_size"] = (600, 400, 400)
        
        await update.message.reply_text(
            "💰 Введите себестоимость упаковки товара (м) в рублях:\n"
            "Например: 25.50",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return COST
        
    elif choice == "Ввести размеры коробки вручную":
        await update.message.reply_text(
            "📏 Введите размеры коробки в мм (ДxШxВ через пробел):\n"
            "Например: 500 300 300",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return CUSTOM_BOX
    
    else:
        keyboard = [
            [KeyboardButton("Коробка 600x400x400")],
            [KeyboardButton("Ввести размеры коробки вручную")],
            [KeyboardButton("Отмена")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "Пожалуйста, выберите один из вариантов:",
            reply_markup=reply_markup
        )
        return BOX_CHOICE

# Получаем свои размеры коробки
async def custom_box(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Отмена":
        return await cancel(update, context)
    
    try:
        box_dimensions = list(map(float, update.message.text.strip().split()))
        if len(box_dimensions) != 3:
            raise ValueError
        
        for dim in box_dimensions:
            if dim <= 0:
                raise ValueError
        
        context.user_data["box_size"] = tuple(box_dimensions)
        
        await update.message.reply_text(
            "💰 Введите себестоимость упаковки товара (м) в рублях:\n"
            "Например: 25.50",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return COST
        
    except:
        await update.message.reply_text(
            "❌ Неверный формат! Введите три положительных числа через пробел:\n"
            "Например: 500 300 300",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return CUSTOM_BOX

# Получаем себестоимость
async def get_cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Отмена":
        return await cancel(update, context)
    
    try:
        cost = float(update.message.text.replace(",", "."))
        if cost <= 0:
            raise ValueError
            
        context.user_data["m"] = cost
        
        await update.message.reply_text(
            "⏱️ Введите время на упаковку товара в секундах:\n"
            "Например: 120 (2 минуты)",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return TIME
        
    except:
        await update.message.reply_text(
            "❌ Введите положительное число:\n"
            "Например: 25.50",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return COST

# Получаем время
async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Отмена":
        return await cancel(update, context)
    
    try:
        time_seconds = float(update.message.text.replace(",", "."))
        if time_seconds <= 0:
            raise ValueError
            
        context.user_data["time_seconds"] = time_seconds
        
        if context.user_data['fulfillment_type'] == "ФБС":
            # Для ФБС запрашиваем среднее количество заказов
            await update.message.reply_text(
                "📊 Введите среднее количество заказов клиента в месяц:\n"
                "Например: 150",
                reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
            )
            return AVG_ORDERS
        else:
            # Для ФБО сразу переходим к расчету
            return await calculate_and_report(update, context)
        
    except:
        await update.message.reply_text(
            "❌ Введите положительное число:\n"
            "Например: 120",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return TIME

# Получаем среднее количество заказов для ФБС
async def get_avg_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Отмена":
        return await cancel(update, context)
    
    try:
        avg_orders = int(update.message.text)
        if avg_orders <= 0:
            raise ValueError
            
        context.user_data["avg_orders"] = avg_orders
        return await calculate_and_report(update, context)
        
    except:
        await update.message.reply_text(
            "❌ Введите целое положительное число:\n"
            "Например: 150",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        return AVG_ORDERS

# Улучшенный алгоритм расчета упаковки
def calculate_packaging(dimensions, box_size):
    """
    Рассчитывает все возможные варианты упаковки товара в коробку
    с учетом всех ориентаций и комбинаций
    """
    l, w, h = dimensions
    box_l, box_w, box_h = box_size
    
    # Все возможные ориентации товара (6 вариантов)
    orientations = [
        (l, w, h), (l, h, w),
        (w, l, h), (w, h, l),
        (h, l, w), (h, w, l)
    ]
    
    best_result = None
    max_items = 0
    
    for ol, ow, oh in orientations:
        # Пропускаем если товар больше коробки
        if ol > box_l or ow > box_w or oh > box_h:
            continue
        
        # Рассчитываем сколько поместится
        fit_l = int(box_l // ol)
        fit_w = int(box_w // ow)
        fit_h = int(box_h // oh)
        
        total = fit_l * fit_w * fit_h
        
        if total > max_items:
            max_items = total
            # Рассчитываем остаточное пространство
            space_l = box_l - fit_l * ol
            space_w = box_w - fit_w * ow
            space_h = box_h - fit_h * oh
            
            best_result = {
                'total': total,
                'orientation': (ol, ow, oh),
                'layout': (fit_l, fit_w, fit_h),
                'waste_l': space_l,
                'waste_w': space_w,
                'waste_h': space_h,
                'waste_volume': space_l * space_w * space_h
            }
    
    return best_result

# Расчет НР по новой формуле
def calculate_nr(x):
    """
    Рассчитывает НР по формуле: 57000 / (16000 + x)
    где x - среднее количество заказов для ФБС или размер партии для ФБО
    """
    return 57000 / (16000 + x)

# Производим расчет и выводим результат
async def calculate_and_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        fulfillment_type = context.user_data['fulfillment_type']
        item_name = context.user_data.get('item_name', 'Товар')
        
        if fulfillment_type == "ФБС":
            # Расчет для ФБС
            time_seconds = context.user_data["time_seconds"]
            avg_orders = context.user_data["avg_orders"]
            
            time_hours = time_seconds / 3600
            t = time_hours * HOURLY_RATE
            m = context.user_data["m"]
            nr = calculate_nr(avg_orders)  # Новая формула НР
            
            # Базовая стоимость без наценки
            base_cost = m + t + nr
            total_cost_per_item = base_cost * (1 + MARKUP)
            profit_per_item = total_cost_per_item - base_cost
            
            report = (
                f"📦 *ОТЧЁТ ПО УПАКОВКЕ (ФБС)*\n"
                f"═══════════════════════\n"
                f"*Товар:* {item_name}\n"
                f"*Тип:* ФБС\n"
                f"*Среднее заказов в месяц:* {avg_orders} шт.\n\n"
                f"*РАСЧЁТ НА 1 ТОВАР:*\n"
                f"• Материалы : {m:.2f} руб.\n"
                f"• Время: {time_seconds} сек. ({time_hours:.3f} ч.)\n"
                f"• Стоимость времени : {t:.2f} руб.\n"
                f"• Накладные расходы (57000/(16000+{avg_orders})): {nr:.2f} руб.\n"
                f"• Сумма затрат: {base_cost:.2f} руб.\n"
                f"═══════════════════════\n"
                f"*ИТОГО НА 1 ТОВАР:*\n"
                f"📊 *Стоимость упаковки:* {total_cost_per_item:.2f} руб.\n"
                f"💰 *Чистая прибыль:* {profit_per_item:.2f} руб.\n"
                f"📈 *Рентабельность:* {(profit_per_item/total_cost_per_item*100):.0f}%"
            )
            
        else:  # ФБО
            dimensions = context.user_data["dimensions"]
            quantity = context.user_data["quantity"]
            box_size = context.user_data["box_size"]
            m_per_item = context.user_data["m"]
            time_per_item = context.user_data["time_seconds"]
            
            # Рассчитываем упаковку
            packing_result = calculate_packaging(dimensions, box_size)
            
            if not packing_result:
                await update.message.reply_text(
                    f"❌ Товар {dimensions[0]}x{dimensions[1]}x{dimensions[2]} мм "
                    f"не помещается в коробку {box_size[0]}x{box_size[1]}x{box_size[2]} мм!",
                    reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/start")]], resize_keyboard=True)
                )
                return ConversationHandler.END
            
            items_per_box = packing_result['total']
            boxes_needed = math.ceil(quantity / items_per_box)
            
            # Расчет для одного товара
            time_hours_per_item = time_per_item / 3600
            t_per_item = time_hours_per_item * HOURLY_RATE
            nr_per_item = calculate_nr(quantity)  # НР зависит от размера партии
            
            # Базовая стоимость одного товара без наценки
            base_cost_per_item = m_per_item + t_per_item + nr_per_item
            
            # Стоимость с наценкой и скидкой 10% для ФБО
            cost_per_item_with_markup = base_cost_per_item * (1 + MARKUP)
            cost_per_item_with_discount = cost_per_item_with_markup * (1 - FBO_DISCOUNT)  # Скидка 10%
            
            # Общая стоимость партии
            total_cost = cost_per_item_with_discount * quantity
            
            # Чистая прибыль (с учетом скидки)
            total_base_cost = base_cost_per_item * quantity
            total_profit = total_cost - total_base_cost
            profit_per_item = total_profit / quantity
            
            # Формируем отчет
            report = (
                f"📦 *ОТЧЁТ ПО УПАКОВКЕ (ФБО)*\n"
                f"═══════════════════════\n"
                f"*Товар:* {item_name}\n"
                f"*Тип:* ФБО\n"
                f"*Габариты:* {dimensions[0]}x{dimensions[1]}x{dimensions[2]} мм\n"
                f"*Партия:* {quantity} шт.\n"
                f"*Коробка:* {box_size[0]}x{box_size[1]}x{box_size[2]} мм\n\n"
                
                f"*УПАКОВКА:*\n"
                f"• Ориентация товара: {packing_result['orientation'][0]}x"
                f"{packing_result['orientation'][1]}x{packing_result['orientation'][2]} мм\n"
                f"• Раскладка в коробке: {packing_result['layout'][0]}×"
                f"{packing_result['layout'][1]}×{packing_result['layout'][2]} шт.\n"
                f"• Товаров в коробке: {items_per_box} шт.\n"
                f"• Нужно коробок: {boxes_needed} шт.\n"
                f"• Остаток места: {packing_result['waste_volume']/1000000:.3f} л\n\n"
                
                f"*РАСЧЁТ НА 1 ТОВАР:*\n"
                f"• Материалы (м): {m_per_item:.2f} руб.\n"
                f"• Время: {time_per_item} сек. ({time_hours_per_item:.3f} ч.)\n"
                f"• Стоимость времени (т): {t_per_item:.2f} руб.\n"
                f"• Накладные расходы (57000/(16000+{quantity})): {nr_per_item:.2f} руб.\n"
                f"• Сумма затрат: {base_cost_per_item:.2f} руб.\n"
                f"• Стоимость с наценкой: {cost_per_item_with_markup:.2f} руб.\n"
                f"═══════════════════════\n"
                f"*ИТОГО ДЛЯ ПАРТИИ:*\n"
                f"📊 *Общая стоимость упаковки:* {total_cost:.2f} руб.\n"
                f"📦 *На 1 товар:* {cost_per_item_with_discount:.2f} руб.\n"
                f"📦 *На 1 коробку:* {total_cost/boxes_needed:.2f} руб.\n"
                f"💰 *Общая прибыль:* {total_profit:.2f} руб.\n"
                f"💰 *Прибыль на 1 товар:* {profit_per_item:.2f} руб.\n"
                f"📈 *Рентабельность:* {(total_profit/total_cost*100):.0f}%"
            )
        
        # Отправляем отчет
        await update.message.reply_text(
            report,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/start")]], resize_keyboard=True)
        )
        
        # Предлагаем начать заново
        await update.message.reply_text(
            "Для нового расчета нажмите /start",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/start")]], resize_keyboard=True)
        )
        
    except Exception as e:
        logger.error(f"Error in calculation: {e}")
        await update.message.reply_text(
            "❌ Ошибка расчета. Проверьте введенные данные и попробуйте снова.\n"
            "Нажмите /start чтобы начать заново.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/start")]], resize_keyboard=True)
        )
    
    return ConversationHandler.END

# Отмена диалога
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Расчёт отменён. Нажмите /start чтобы начать заново.",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/start")]], resize_keyboard=True)
    )
    return ConversationHandler.END

# Команда help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📋 *Помощь по боту-калькулятору*\n\n"
        "*/start* - начать расчет стоимости упаковки\n"
        "*/help* - показать это сообщение\n\n"
        
        "*Формула расчета:*\n"
        "(м + т + нр) × (1 + 200%) = цена упаковки\n"
        "• м - себестоимость материалов на 1 товар\n"
        "• т = (время в секундах / 3600) × 350 руб.\n"
        "• нр = 57000 / (16000 + X)\n"
        "   - для ФБС: X = среднее количество заказов в месяц\n"
        "   - для ФБО: X = размер партии\n\n"
        
        "*Особенности:*\n"
        "• Для ФБО применяется скидка 10%\n"
        "• Для ФБО рассчитывается оптимальная упаковка в коробку"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/start")]], resize_keyboard=True)
    )

def main() -> None:
    # ⚠️ ЗАМЕНИТЕ НА ВАШ РЕАЛЬНЫЙ ТОКЕН
    BOT_TOKEN = "8504882605:AAH4QFAEI6SUvaWiPxSHZXwwPYQ-PNdTHak"
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Создаём ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FULFILLMENT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, fulfillment_type)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            DIMENSIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_dimensions)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quantity)],
            BOX_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, box_choice)],
            CUSTOM_BOX: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_box)],
            COST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_cost)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)],
            AVG_ORDERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_avg_orders)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("start", start))
    
    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()